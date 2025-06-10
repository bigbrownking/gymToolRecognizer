import logging
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from PIL import Image
import io

from project.core.database import get_db, get_image_from_minio
from project.cv.GymToolRecognizer import GymToolRecognizer
from project.model.gymtool import GymTool
from project.core.security import get_current_user
from project.model.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["cv"])

recognizer = GymToolRecognizer("project/cv/model.pth")


@router.post(
    "/predict",
    summary="Predict gym tool from uploaded image",
    description="""
Upload a photo of a gym tool (equipment) and receive prediction results, 
including tool name, description, associated muscles, and confidence score.

Subscription required after free attempts are exhausted.
""",
    responses={
        200: {
            "description": "Successful prediction or informative rejection",
            "content": {
                "application/json": {
                    "examples": {
                        "Prediction Success": {
                            "summary": "Gym tool detected",
                            "value": {
                                "is_gym_tool": True,
                                "class_id": 3,
                                "class_name": "dumbbell",
                                "name": "Dumbbell",
                                "description": "A short bar with weights...",
                                "links": ["https://example.com/dumbbell1"],
                                "alternative": "Barbell",
                                "muscles": [
                                    {
                                        "name": "Biceps",
                                        "primary": True,
                                        "secondary": False,
                                        "image_b64": "<base64string>"
                                    }
                                ],
                                "confidence": 0.92,
                                "entropy": 0.15,
                                "requested_by": "user@example.com",
                                "free_attempts_left": 2
                            }
                        },
                        "Prediction Failure": {
                            "summary": "Image not recognized",
                            "value": {
                                "is_gym_tool": False,
                                "message": "No gym tool detected",
                                "reason": "Low confidence",
                                "confidence": 0.45,
                                "entropy": 0.89,
                                "requested_by": "user@example.com",
                                "free_attempts_left": 1,
                                "suggestions": [
                                    "Please upload an image of gym equipment",
                                    "Make sure the gym tool is clearly visible",
                                    "Avoid images with multiple objects or unclear backgrounds"
                                ]
                            }
                        }
                    }
                }
            }
        },
        403: {"description": "No free attempts left"},
        500: {"description": "Internal server error"}
    }
)
async def predict(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    logger.info(f"Received image for prediction from user: {current_user.email}")

    try:
        if not current_user.is_sub:
            if current_user.free_attempts <= 0:
                logger.warning(f"No free attempts left for user: {current_user.email}")
                return {"error": "No free attempts left. Please subscribe to continue."}

            current_user.free_attempts -= 1
            db.commit()
            logger.info(f"Decreased attempt. Remaining: {current_user.free_attempts}")

        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        logger.info(f"Image successfully loaded into memory. Original mode: {image.mode}")

        # Ensure image is in RGB mode early to prevent issues
        if image.mode != 'RGB':
            if image.mode in ('RGBA', 'LA', 'P'):
                # Handle transparency properly
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                if image.mode in ('RGBA', 'LA'):
                    background.paste(image, mask=image.split()[-1])
                    image = background
                else:
                    image = background
            else:
                image = image.convert('RGB')
            logger.info(f"Converted image to RGB mode")

        # Get prediction with validation
        prediction_result = recognizer.predict_image(image)

        # Check if image was identified as a gym tool
        if not prediction_result["is_gym_tool"]:
            logger.info(f"Image rejected: {prediction_result['message']}")
            return {
                "is_gym_tool": False,
                "message": prediction_result["message"],
                "reason": prediction_result["reason"],
                "confidence": prediction_result.get("confidence", 0),
                "entropy": prediction_result.get("entropy", 0),
                "requested_by": current_user.email,
                "free_attempts_left": current_user.free_attempts if not current_user.is_sub else "∞",
                "suggestions": [
                    "Please upload an image of gym equipment",
                    "Make sure the gym tool is clearly visible",
                    "Avoid images with multiple objects or unclear backgrounds"
                ]
            }

        predicted_id = prediction_result["predicted_class"]
        predicted_name = prediction_result["class_name"]
        confidence_score = prediction_result["confidence"]

        logger.info(f"Model predicted class ID: {predicted_id} with confidence: {confidence_score:.4f}")

        gym_tools = db.query(GymTool).all()
        if not gym_tools:
            logger.warning("No gym tools found in database.")
            return {"error": "No gym tools found in database."}

        gym_tool = db.query(GymTool).filter(GymTool.name == predicted_name).first()
        if not gym_tool:
            logger.warning(f"Predicted ID {predicted_id} not found in DB.")
            return {"error": "Predicted gym tool not found in database."}

        muscles_info = []
        for assoc in gym_tool.muscle_associations:
            muscle_data = {
                "основные мышцы": assoc.primary_muscles,
                "второстепенные мышцы": assoc.secondary_muscles,
            }

            if assoc.muscle.image_url:
                muscle_data["image_url"] = assoc.muscle.image_url
            muscles_info.append(muscle_data)

        response = {
            "is_gym_tool": True,
            "class_id": gym_tool.id,
            "class_name": predicted_name,
            "name": gym_tool.name,
            "description": gym_tool.description,
            "links": gym_tool.links,
            "alternative": gym_tool.alternative,
            "muscles": muscles_info,
            "confidence": confidence_score,
            "entropy": prediction_result.get("entropy"),
            "requested_by": current_user.email,
            "free_attempts_left": current_user.free_attempts if not current_user.is_sub else "∞",
        }

        logger.info("Prediction response generated successfully.")
        return response

    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        return {"error": "Internal server error"}
