# 📋 설정 파일
import os

# ===== 모델 설정 =====
MODEL_CONFIG = {
    # 배포 환경에서는 시뮬레이션 모드로 동작 (모델 파일 없음)
    'hrv_model_path': "models/hrv_transformer_model.keras",  # 배포용 경로
    'stress_model_path': "models/stress_model.keras",  # 배포용 경로
    'default_threshold': 0.35,  # 기본 스트레스 임계값
    'demo_mode': True,  # 데모 모드 활성화
}

# ===== 작업자 설정 =====
WORKERS = {
    'worker_1': {'name': '작업자 A', 'color': '#1f77b4'},
    'worker_2': {'name': '작업자 B', 'color': '#ff7f0e'},
    'worker_3': {'name': '작업자 C', 'color': '#2ca02c'},
    'worker_4': {'name': '작업자 D', 'color': '#d62728'},
}

# ===== 대시보드 설정 =====
DASHBOARD_CONFIG = {
    'page_title': "🏭 실시간 작업자 스트레스 모니터링",
    'page_icon': "⚡",
    'layout': "wide",
    'update_interval': 1.0,  # 1초 업데이트
    'max_data_points': 100,  # 그래프에 표시할 최대 데이터 포인트
}

# ===== 시뮬레이션 설정 =====
SIMULATION_CONFIG = {
    'hr_base_range': (70, 90),      # 기본 심박수 범위
    'hr_stress_range': (90, 130),   # 스트레스 상태 심박수 범위
    'noise_level': 5,               # 심박수 노이즈 정도
    'stress_probability': 0.15,     # 스트레스 상태 발생 확률
    'stress_duration': (5, 20),     # 스트레스 지속 시간 범위 (초)
}

# ===== 경고 설정 =====
ALERT_CONFIG = {
    'stress_color': '#FF4B4B',      # 스트레스 감지 시 빨간색
    'normal_color': '#00C851',      # 정상 상태 초록색
    'warning_color': '#FF8800',     # 주의 상태 주황색
    'alert_blink_duration': 3,      # 경고 깜빡임 지속 시간 (초)
}

# ===== CSV 파일 설정 =====
CSV_CONFIG = {
    'required_columns': ['timestamp', 'HR'],  # 필수 컬럼
    'timestamp_formats': [
        '%Y-%m-%d %H:%M:%S',
        '%Y/%m/%d %H:%M:%S',
        '%d/%m/%Y %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f',
    ],
    'max_file_size_mb': 50,  # 최대 파일 크기 (MB)
}

# ===== 디렉토리 설정 =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')

# 디렉토리 생성
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
