from deepface import DeepFace
result = DeepFace.extract_faces(img_path='tests/fixtures/face_known.jpg', enforce_detection=False)
print(len(result), 'face(s) found')
for r in result:
    print('confidence:', r.get('confidence'))
