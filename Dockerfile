FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p cv
ADD project/cv/model.pth cv/model.pth

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]