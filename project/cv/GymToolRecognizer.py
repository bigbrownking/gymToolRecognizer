# import os
# from datetime import datetime
# import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
# from torch.cuda.amp import GradScaler, autocast
# from torch.optim.lr_scheduler import OneCycleLR
# from torch.utils.tensorboard import SummaryWriter
from torchvision import datasets, transforms, models
# from torch.utils.data import DataLoader
# from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from torch.utils.data import WeightedRandomSampler
# import matplotlib.pyplot as plt
from torchvision.transforms import v2

from project.core.converter import CLASS_NAMES

# from tqdm import tqdm
# from sklearn.metrics import classification_report
# from core.converter import CLASS_NAMES

NUM_CLASSES = 33
BATCH_SIZE = 32
EPOCHS = 50
LEARNING_RATE = 1e-5
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {DEVICE}")


class GymToolRecognizer:
    def __init__(self, model_path="model.pth"):
        """Model architecture"""
        self.model = models.resnet50(weights=None)
        in_feats = self.model.fc.in_features
        self.model.fc = nn.Linear(in_feats, NUM_CLASSES)
        self.model = self.model.to(DEVICE)

        self.train_loader = None
        self.val_loader = None
        self.test_loader = None
        self.writer = None

        # Training metrics
        self.train_accuracy = []
        self.val_accuracy = []
        self.test_accuracy = []
        self.best_loss = float('inf')

        # Loss and optimizer
        self.criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
        self.optimizer = optim.AdamW(self.model.parameters(), lr=1e-4, weight_decay=1e-4)
        self.scheduler = None
        self.model_path = model_path
        self.load_model()

    def _get_transforms(self):
        """Return train and val transforms"""
        base_transforms = [
            transforms.Lambda(lambda img: img.convert("RGB")),
            v2.Resize((256, 256)),
            v2.CenterCrop(224),
            v2.ToImage(),
            v2.ToDtype(torch.float32, scale=True),
            v2.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]

        train_transform = v2.Compose(base_transforms[:3] + [
            v2.RandomHorizontalFlip(),
            v2.RandomVerticalFlip(),
            v2.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            v2.RandomAffine(degrees=0, translate=(0.1, 0.1)),
            v2.RandomPerspective(p=0.5),
            *base_transforms[3:]
        ])

        val_transform = v2.Compose(base_transforms)
        self.cutmix = v2.CutMix(num_classes=NUM_CLASSES)

        return train_transform, val_transform

    # def _load_datasets(self):
    #     """Load datasets only when needed"""
    #     train_dir = 'dataset/images/train'
    #     val_dir = 'dataset/images/val'
    #     test_dir = 'dataset/images/test'
    #
    #     # Verify paths
    #     for path in [train_dir, val_dir, test_dir]:
    #         if not os.path.exists(path):
    #             raise FileNotFoundError(f"Dataset directory not found: {path}")
    #
    #     train_transform, val_transform = self._get_transforms()
    #
    #     # Load datasets
    #     train_dataset = datasets.ImageFolder(root=train_dir, transform=train_transform)
    #     val_dataset = datasets.ImageFolder(root=val_dir, transform=val_transform)
    #     test_dataset = datasets.ImageFolder(root=test_dir, transform=val_transform)
    #
    #     # Create balanced sampler
    #     labels = train_dataset.targets
    #     class_counts = np.bincount(labels)
    #     class_weights = 1. / class_counts
    #     sample_weights = [class_weights[label] for label in labels]
    #     sampler = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)
    #
    #     # Create data loaders
    #     self.train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=sampler)
    #     self.val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    #     self.test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)
    #
    #     # Update criterion with class weights
    #     class_weights = 1. / torch.tensor(class_counts, dtype=torch.float32).to(DEVICE)
    #     self.criterion = nn.CrossEntropyLoss(weight=class_weights)

    def save_model(self):
        """Save model weights"""
        torch.save(self.model.state_dict(), self.model_path)
        print(f"Model saved to {self.model_path}")

    def load_model(self):
        """Load model weights"""
        try:
            self.model.load_state_dict(
                torch.load(self.model_path, map_location=DEVICE, weights_only=True)
            )
            self.model.eval()
            print(f"Model loaded from {self.model_path}")
        except FileNotFoundError:
            print(f"No saved model found at {self.model_path}, starting fresh.")

    def predict_image(self, image: Image.Image, confidence_threshold: float = 0.7) -> dict:
        """
        Predict class for a single image with confidence validation
        Returns dict with prediction info or None if not a gym tool
        """
        self.model.eval()

        if image.mode != 'RGB':
            image = image.convert('RGB')

        base_transforms = [
            transforms.Lambda(lambda img: img.convert("RGB")),
            v2.Resize((256, 256)),
            v2.CenterCrop(224),
            v2.ToImage(),
            v2.ToDtype(torch.float32, scale=True),
            v2.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]

        transform = v2.Compose(base_transforms[:3] + [
            v2.RandomHorizontalFlip(),
            v2.RandomVerticalFlip(),
            v2.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            v2.RandomAffine(degrees=0, translate=(0.1, 0.1)),
            v2.RandomPerspective(p=0.5),
            *base_transforms[3:]
        ])

        try:
            image_tensor = transform(image).unsqueeze(0).to(DEVICE)
            print(f"Input tensor shape: {image_tensor.shape}")

            with torch.no_grad():
                outputs = self.model(image_tensor)
                # Apply softmax to get probabilities
                probabilities = torch.nn.functional.softmax(outputs, dim=1)
                confidence, predicted_class = torch.max(probabilities, 1)

                confidence_score = confidence.item()
                predicted_id = predicted_class.item()

                print(f"Predicted class: {predicted_id}, Confidence: {confidence_score:.4f}")

                # Calculate entropy for uncertainty detection
                entropy = -torch.sum(probabilities * torch.log(probabilities + 1e-8), dim=1).item()
                max_entropy = torch.log(torch.tensor(NUM_CLASSES, dtype=torch.float32)).item()
                normalized_entropy = entropy / max_entropy

                print(f"Entropy: {entropy:.4f}, Normalized: {normalized_entropy:.4f}")

                # Check if confidence is above threshold
                if confidence_score < confidence_threshold:
                    return {
                        "is_gym_tool": False,
                        "reason": "low_confidence",
                        "confidence": confidence_score,
                        "entropy": normalized_entropy,
                        "threshold": confidence_threshold,
                        "message": f"Image doesn't appear to be a gym tool (confidence: {confidence_score:.2%})"
                    }

                # Additional check: high entropy indicates uncertainty
                if normalized_entropy > 0.8:  # High uncertainty
                    return {
                        "is_gym_tool": False,
                        "reason": "high_uncertainty",
                        "confidence": confidence_score,
                        "entropy": normalized_entropy,
                        "message": "Image classification is too uncertain - likely not a gym tool"
                    }

                return {
                    "is_gym_tool": True,
                    "predicted_class": predicted_id,
                    "confidence": confidence_score,
                    "entropy": normalized_entropy,
                    "class_name": CLASS_NAMES.get(predicted_id, "Unknown")
                }

        except Exception as e:
            print(f"Error during prediction: {str(e)}")
            raise

    # def train(self):
    #     if self.train_loader is None:
    #         self._load_datasets()
    #     log_dir = os.path.join("logs", datetime.now().strftime("%Y%m%d-%H%M%S"))
    #     os.makedirs(log_dir, exist_ok=True)
    #     self.writer = SummaryWriter(log_dir)
    #     self.optimizer = optim.AdamW(self.model.parameters(), lr=1e-4)
    #     self.scheduler = OneCycleLR(
    #         self.optimizer,
    #         max_lr=3e-4,
    #         steps_per_epoch=len(self.train_loader),
    #         epochs=EPOCHS
    #     )
    #
    #     print("Starting training...")
    #     prev_val_loss = None
    #     best_val_loss = float('inf')
    #     no_improve_count = 0
    #     patience = 5
    #     min_delta = 1e-3
    #     scaler = GradScaler()
    #     try:
    #         for epoch in range(1, EPOCHS + 1):
    #             # Training phase
    #             self.model.train()
    #             running_loss, correct, total = 0.0, 0, 0
    #             progress_bar = tqdm(self.train_loader, desc=f"Epoch {epoch}/{EPOCHS}", leave=False)
    #             for images, labels in progress_bar:
    #                 images, labels = images.to(DEVICE), labels.to(DEVICE)
    #                 images, labels = self.cutmix(images, labels)
    #
    #                 self.optimizer.zero_grad()
    #
    #                 # Forward pass with mixed precision
    #                 with autocast():
    #                     outputs = self.model(images)
    #                     loss = self.criterion(outputs, labels)
    #
    #                 # Backward pass
    #                 scaler.scale(loss).backward()
    #                 scaler.step(self.optimizer)
    #                 scaler.update()
    #                 self.scheduler.step()
    #
    #                 # Metrics
    #                 preds = outputs.argmax(dim=1)
    #                 true_labels = labels.argmax(dim=1) if len(labels.shape) > 1 else labels
    #                 correct += (preds == true_labels).sum().item()
    #                 total += labels.size(0)
    #                 running_loss += loss.item()
    #                 progress_bar.set_postfix(loss=loss.item())
    #
    #             train_acc = correct / total
    #             self.train_accuracy.append(train_acc)
    #             self.writer.add_scalar('Accuracy/train', train_acc, epoch)
    #             print(f"Epoch {epoch}/{EPOCHS}, Accuracy: {train_acc * 100:.4f}%")
    #
    #             # Validation phase
    #             self.model.eval()
    #             val_loss, val_preds, val_labels = 0.0, [], []
    #             with torch.no_grad():
    #                 for images, labels in self.val_loader:
    #                     images, labels = images.to(DEVICE), labels.to(DEVICE)
    #                     outputs = self.model(images)
    #                     loss = self.criterion(outputs, labels)
    #                     val_loss += loss.item()
    #                     preds = outputs.argmax(dim=1)
    #                     val_preds.extend(preds.cpu().numpy())
    #                     val_labels.extend(labels.cpu().numpy())
    #
    #             avg_val_loss = val_loss / len(self.val_loader)
    #             val_acc = (np.array(val_preds) == np.array(val_labels)).mean()
    #             self.val_accuracy.append(val_acc)
    #             self.writer.add_scalar('Loss/val', avg_val_loss, epoch)
    #             self.writer.add_scalar('Accuracy/val', val_acc, epoch)
    #             self.writer.add_scalar('Learning Rate', self.optimizer.param_groups[0]['lr'], epoch)
    #             print(f"Epoch {epoch}/{EPOCHS}, Val Acc: {val_acc * 100:.4f}%")
    #
    #             # Learning rate scheduling
    #             if isinstance(self.scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
    #                 self.scheduler.step(avg_val_loss)
    #
    #             # Early stopping and model saving
    #             if avg_val_loss < best_val_loss:
    #                 best_val_loss = avg_val_loss
    #                 self.save_model()
    #                 print("Checkpoint saved (best val loss).")
    #             if prev_val_loss is not None and abs(prev_val_loss - avg_val_loss) < min_delta:
    #                 no_improve_count += 1
    #                 if no_improve_count >= patience:
    #                     print("Early stopping triggered.")
    #                     self.writer.close()
    #                     print(f"TensorBoard logs written to: {self.writer.log_dir}")
    #                     self.calculate_metrics()
    #                     break
    #             else:
    #                 no_improve_count = 0
    #             prev_val_loss = avg_val_loss
    #
    #             # Testing phase
    #             test_preds, test_labels = [], []
    #             with torch.no_grad():
    #                 for images, labels in self.test_loader:
    #                     images, labels = images.to(DEVICE), labels.to(DEVICE)
    #                     outputs = self.model(images)
    #                     preds = outputs.argmax(dim=1)
    #                     test_preds.extend(preds.cpu().numpy())
    #                     test_labels.extend(labels.cpu().numpy())
    #             test_acc = (np.array(test_preds) == np.array(test_labels)).mean()
    #             self.test_accuracy.append(test_acc)
    #             print(f"Epoch {epoch}/{EPOCHS}, Test Acc: {test_acc * 100:.4f}%")
    #
    #             # Periodic saving
    #             if epoch % 10 == 0:
    #                 self.save_model()
    #                 print(f"Checkpoint saved at {self.model_path}")
    #
    #         self.writer.close()
    #         print(f"TensorBoard logs written to: {self.writer.log_dir}")
    #         self.calculate_metrics()
    #
    #     except KeyboardInterrupt:
    #         print("\nTraining interrupted by user. Saving final metrics...")
    #         self.save_model()
    #         self.calculate_metrics()
    #         self.writer.close()
    #         print("Metrics and model saved before exiting.")
    #         raise
    #
    # def calculate_metrics(self):
    #     self.model.eval()
    #     predictions, true_labels = [], []
    #     test_running_loss = 0.0
    #
    #     with torch.no_grad():
    #         for images, labels in self.test_loader:
    #             images, labels = images.to(DEVICE), labels.to(DEVICE)
    #             outputs = self.model(images)
    #             loss = self.criterion(outputs, labels)
    #             test_running_loss += loss.item()
    #             _, preds = torch.max(outputs, 1)
    #             predictions.extend(preds.cpu().numpy())
    #             true_labels.extend(labels.cpu().numpy())
    #
    #     # Calculate metrics
    #     final_test_loss = test_running_loss / len(self.test_loader)
    #     final_test_accuracy = (np.array(predictions) == np.array(true_labels)).mean()
    #     precision = precision_score(true_labels, predictions, average='macro', zero_division=0)
    #     recall = recall_score(true_labels, predictions, average='macro', zero_division=0)
    #     f1 = f1_score(true_labels, predictions, average='macro', zero_division=0)
    #     conf_matrix = confusion_matrix(true_labels, predictions)
    #
    #     target_names = [CLASS_NAMES[i] for i in range(NUM_CLASSES)]
    #     report = classification_report(true_labels, predictions, target_names=target_names, zero_division=0)
    #     # Save results
    #     base_dir = "results"
    #     os.makedirs(base_dir, exist_ok=True)
    #     existing_folders = [int(name) for name in os.listdir(base_dir) if name.isdigit()]
    #     next_folder = str(max(existing_folders) + 1) if existing_folders else "1"
    #     save_dir = os.path.join(base_dir, next_folder)
    #     os.makedirs(save_dir, exist_ok=True)
    #
    #     with open(os.path.join(save_dir, "metrics.txt"), "w") as f:
    #         f.write("\nFinal Test Metrics:\n")
    #         f.write(f"Test Loss: {final_test_loss:.6f}\n")
    #         f.write(f"Test Accuracy: {final_test_accuracy * 100:.4f}\n")
    #         f.write(f"Precision (Macro): {precision * 100:.4f}\n")
    #         f.write(f"Recall (Macro): {recall * 100:.4f}\n")
    #         f.write(f"F1-Score (Macro): {f1 * 100:.4f}\n")
    #         f.write(f"Confusion Matrix:\n{conf_matrix}\n")
    #         f.write("Classification Report:\n")
    #         f.write(report)
    #
    #     print(f"Metrics saved to {save_dir}/metrics.txt")
    #     self.plot_accuracy(save_dir)
    #
    # def plot_accuracy(self, save_dir):
    #     plt.figure(figsize=(10, 6))
    #
    #     train_percentages = [a * 100 for a in self.train_accuracy]
    #     val_percentages = [a * 100 for a in self.val_accuracy]
    #     test_percentages = [a * 100 for a in self.test_accuracy]
    #
    #     plt.plot(range(1, len(train_percentages) + 1), train_percentages, label='Training Accuracy', marker='o')
    #     plt.plot(range(1, len(val_percentages) + 1), val_percentages, label='Validation Accuracy', marker='s')
    #     plt.plot(range(1, len(test_percentages) + 1), test_percentages, label='Test Accuracy', marker='x')
    #
    #     plt.xlabel('Epochs')
    #     plt.ylabel('Accuracy (%)')
    #     plt.title('Accuracy Over Epochs')
    #     plt.legend()
    #     plt.grid()
    #
    #     plot_path = os.path.join(save_dir, 'accuracy_plot.png')
    #     plt.savefig(plot_path)
    #     plt.close()
    #     print(f"Accuracy plot saved as '{plot_path}'")


# if __name__ == "__main__":

    # recognizer = GymToolRecognizer()
    # recognizer._load_datasets()
    #
    # print("\nDataset Statistics:")
    # print(f"Train samples: {len(recognizer.train_loader.dataset)}")
    # print(f"Val samples: {len(recognizer.val_loader.dataset)}")
    # print(f"Test samples: {len(recognizer.test_loader.dataset)}")
    #
    # train_dataset = recognizer.train_loader.dataset
    # train_targets = np.array(train_dataset.targets)
    # train_counts = np.bincount(train_targets)
    #
    # print("\nTrain samples per class:")
    # for i, count in enumerate(train_counts):
    #     print(f"{train_dataset.classes[i]}: {count}")
    # recognizer.calculate_metrics()
    # recognizer.train()
