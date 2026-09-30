import os
from pathlib import Path
import re
import tempfile

import cv2
from flask import Flask, render_template, request, redirect, url_for, send_from_directory

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
TEMP_ROOT = Path(tempfile.gettempdir()) / 'gender_age_web'
UPLOAD_FOLDER = TEMP_ROOT / 'uploads'
RESULT_FOLDER = TEMP_ROOT / 'results'

os.makedirs(str(UPLOAD_FOLDER), exist_ok=True)
os.makedirs(str(RESULT_FOLDER), exist_ok=True)

faceProto = str(BASE_DIR / 'opencv_face_detector.pbtxt')
faceModel = str(BASE_DIR / 'opencv_face_detector_uint8.pb')
ageProto = str(BASE_DIR / 'age_deploy.prototxt')
ageModel = str(BASE_DIR / 'age_net.caffemodel')
genderProto = str(BASE_DIR / 'gender_deploy.prototxt')
genderModel = str(BASE_DIR / 'gender_net.caffemodel')
MODEL_MEAN_VALUES = (78.4263377603, 87.7689143744, 114.895847746)
ageList = ['(0-2)', '(4-6)', '(8-12)', '(15-20)', '(25-32)', '(38-43)', '(48-53)', '(60-100)']
genderList = ['Male', 'Female']

faceNet = cv2.dnn.readNet(faceModel, faceProto)
ageNet = cv2.dnn.readNet(ageModel, ageProto)
genderNet = cv2.dnn.readNet(genderModel, genderProto)


def highlight_face(net, frame, conf_threshold=0.7):
    frame_opencv_dnn = frame.copy()
    frame_height = frame_opencv_dnn.shape[0]
    frame_width = frame_opencv_dnn.shape[1]
    blob = cv2.dnn.blobFromImage(frame_opencv_dnn, 1.0, (300, 300), [104, 117, 123], True, False)
    net.setInput(blob)
    detections = net.forward()
    face_boxes = []

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_threshold:
            x1 = int(detections[0, 0, i, 3] * frame_width)
            y1 = int(detections[0, 0, i, 4] * frame_height)
            x2 = int(detections[0, 0, i, 5] * frame_width)
            y2 = int(detections[0, 0, i, 6] * frame_height)
            face_boxes.append([x1, y1, x2, y2])
            cv2.rectangle(frame_opencv_dnn, (x1, y1), (x2, y2), (0, 255, 0), 2)

    return frame_opencv_dnn, face_boxes


def detect_from_image(image_path):
    frame = cv2.imread(str(image_path))
    if frame is None:
        return None, 'Unable to read the uploaded image.'

    result_img, face_boxes = highlight_face(faceNet, frame)
    if not face_boxes:
        return None, 'No face detected in this image.'

    predictions = []
    padding = 20
    for face_box in face_boxes:
        x1, y1, x2, y2 = face_box
        face = frame[max(0, y1 - padding): min(y2 + padding, frame.shape[0] - 1),
                    max(0, x1 - padding): min(x2 + padding, frame.shape[1] - 1)]

        if face.size == 0:
            continue

        blob = cv2.dnn.blobFromImage(face, 1.0, (227, 227), MODEL_MEAN_VALUES, swapRB=False)
        genderNet.setInput(blob)
        gender_preds = genderNet.forward()
        gender = genderList[gender_preds[0].argmax()]

        ageNet.setInput(blob)
        age_preds = ageNet.forward()
        age = ageList[age_preds[0].argmax()]

        label = f'{gender} {age}'
        cv2.putText(result_img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
        predictions.append({'gender': gender, 'age': age})

    safe_name = re.sub(r'[^A-Za-z0-9_.-]+', '_', image_path.name)
    output_name = f"detected_{safe_name}"
    output_path = RESULT_FOLDER / output_name
    cv2.imwrite(str(output_path), result_img)

    breakdown = predictions[0] if predictions else {'gender': 'Unknown', 'age': '(0-2)'}
    return output_name, breakdown


@app.route('/')
def index():
    return render_template('index.html', result=None, image=None, prediction=None)


@app.route('/results/<path:filename>')
def serve_result(filename):
    return send_from_directory(str(RESULT_FOLDER), filename)


@app.route('/predict', methods=['POST'])
def predict():
    if 'image' not in request.files:
        return redirect(url_for('index'))

    file = request.files['image']
    if file.filename == '':
        return redirect(url_for('index'))

    safe_filename = re.sub(r'[^A-Za-z0-9_.-]+', '_', file.filename)
    filename = safe_filename
    save_path = UPLOAD_FOLDER / filename
    file.save(save_path)

    result_name, prediction = detect_from_image(save_path)
    if not result_name:
        return render_template('index.html', result=prediction, image=None, prediction=None)

    image_url = url_for('serve_result', filename=result_name)
    return render_template('index.html', result=None, image=image_url, prediction=prediction)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
