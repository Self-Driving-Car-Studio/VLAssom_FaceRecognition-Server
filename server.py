import base64
import numpy as np
import cv2
import uvicorn
import socketio
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- 1. FastAPI 앱 설정 ---
app = FastAPI()

# (선택) FastAPI의 CORS 설정. 
# Socket.IO는 자체 cors_allowed_origins가 있지만, 
# 나중에 HTTP 요청도 쓰게 될 경우를 대비해 설정합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 모든 출처 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. Socket.IO 서버 설정 ---
# async_mode='asgi': FastAPI(ASGI)와 함께 실행
# cors_allowed_origins='*': Expo Go 등 모든 클라이언트의 연결을 허용
sio = socketio.AsyncServer(
    async_mode='asgi', 
    cors_allowed_origins='*',
    max_http_buffer_size=10_000_000  # 10MB
)

# Socket.IO 앱을 ASGI 앱으로 래핑
sio_app = socketio.ASGIApp(sio)

# --- 3. FastAPI에 Socket.IO 앱 마운트 ---
# "/socket.io" 경로로 오는 요청은 sio_app(Socket.IO)이 처리합니다.
# socket.io-client는 기본적으로 이 경로로 접속을 시도합니다.
app.mount("/socket.io", sio_app)


# --- (선택) FastAPI가 잘 작동하는지 테스트용 루트 엔드포인트 ---
@app.get("/")
async def root():
    return {"message": "FastAPI 서버가 실행 중입니다."}


# --- 4. Socket.IO 이벤트 핸들러 정의 ---
@sio.event
async def connect(sid, environ):
    print(f"✅ 클라이언트 연결됨: {sid}")

@sio.event
async def disconnect(sid):
    print(f"❌ 클라이언트 연결 끊김: {sid}")

@sio.on('identify-face')
async def handle_identify_face(sid, base64_image):
    """
    Expo 앱의 'identify-face' 이벤트를 처리하는 메인 핸들러
    (함수 이름은 'identify_face'가 아니어도 되지만, 
     가독성을 위해 'handle_'을 붙였습니다.)
    """
    print(f"📸 {sid}로부터 이미지 수신 (크기: {len(base64_image)} bytes)")

    try:
        # --- Base64 이미지 디코딩 ---
        # ... (이하 디코딩 및 얼굴 인식 로직은 모두 동일) ...
        if ',' in base64_image:
            header, base64_data = base64_image.split(',', 1)
        else:
            base64_data = base64_image

        img_data = base64.b64decode(base64_data)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            print(f"⚠️ {sid}: 이미지 디코딩 실패")
            return

        # ... (얼굴 인식 로직 시뮬레이션) ...
        await asyncio.sleep(0.5) 
        user = {"id": "p123", "name": "김철수"}

        # --- 클라이언트로 응답 전송 ---
        await sio.emit('auth-success', user, to=sid)
        print(f"✅ {sid}에게 인증 성공 전송: {user['name']}")

    except Exception as e:
        print(f"🚨 처리 중 오류 발생: {e}")
        await sio.emit('auth-fail', to=sid)


# --- 5. Uvicorn 서버 실행 ---
if __name__ == "__main__":
    print("🚀 FastAPI + Socket.IO 서버를 시작합니다...")
    # host="0.0.0.0": 로컬 네트워크의 모든 IP에서 접속 허용
    # (Expo Go가 PC의 IP로 접속하기 위해 필수!)
    uvicorn.run(app, host="0.0.0.0", port=3000)