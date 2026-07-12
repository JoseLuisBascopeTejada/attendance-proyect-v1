FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir "opencv-python==4.11.0.86"
RUN python -c "import cv2,os,urllib.request; \
    p=os.path.join(os.path.dirname(cv2.__file__),'data'); \
    os.makedirs(p,exist_ok=True); \
    urllib.request.urlretrieve('https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/haarcascade_frontalface_default.xml', os.path.join(p,'haarcascade_frontalface_default.xml'))"
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]