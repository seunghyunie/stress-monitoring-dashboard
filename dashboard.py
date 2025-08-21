# 🖥️ Streamlit 웹 대시보드 - 실시간 스트레스 모니터링
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta
import numpy as np

# 로컬 모듈 임포트
from config import DASHBOARD_CONFIG, WORKERS, ALERT_CONFIG, CSV_CONFIG
from stress_predictor import get_predictor
from data_simulator import MultiWorkerSimulator, generate_demo_csv_data

# ===== 페이지 설정 =====
st.set_page_config(
    page_title=DASHBOARD_CONFIG['page_title'],
    page_icon=DASHBOARD_CONFIG['page_icon'],
    layout=DASHBOARD_CONFIG['layout'],
    initial_sidebar_state="expanded"
)

# ===== 세션 상태 초기화 =====
def initialize_session_state():
    """세션 상태 초기화"""
    if 'predictor' not in st.session_state:
        st.session_state.predictor = get_predictor()
    
    if 'simulator' not in st.session_state:
        st.session_state.simulator = MultiWorkerSimulator()
    
    if 'worker_data' not in st.session_state:
        st.session_state.worker_data = {worker_id: [] for worker_id in WORKERS.keys()}
    
    if 'is_simulation_running' not in st.session_state:
        st.session_state.is_simulation_running = False
    
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = {}
    
    if 'alert_states' not in st.session_state:
        st.session_state.alert_states = {worker_id: False for worker_id in WORKERS.keys()}

# ===== 유틸리티 함수들 =====
def parse_timestamp(timestamp_str):
    """다양한 형식의 타임스탬프 파싱"""
    for fmt in CSV_CONFIG['timestamp_formats']:
        try:
            return pd.to_datetime(timestamp_str, format=fmt)
        except:
            continue
    
    # 기본 pandas 파싱 시도
    try:
        return pd.to_datetime(timestamp_str)
    except:
        return None

def process_uploaded_csv(uploaded_file, worker_id):
    """업로드된 CSV 파일 처리"""
    try:
        # CSV 읽기
        df = pd.read_csv(uploaded_file)
        
        # 필수 컬럼 확
        required_cols = CSV_CONFIG['required_columns']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return None, f"필수 컬럼이 없습니다: {missing_cols}"
        
        # 타임스탬프 파싱
        df['timestamp'] = df['timestamp'].apply(parse_timestamp)
        invalid_timestamps = df['timestamp'].isna().sum()
        
        if invalid_timestamps > 0:
            st.warning(f"⚠️ {invalid_timestamps}개의 잘못된 타임스탬프가 발견되어 제거됩니다.")
            df = df.dropna(subset=['timestamp'])
        
        # HR 데이터 유효성 검사
        df = df[(df['HR'] >= 30) & (df['HR'] <= 200)]  # 합리적인 심박수 범위
        
        # 정렬
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df, None
        
    except Exception as e:
        return None, f"파일 처리 오류: {e}"

def update_worker_data(worker_id, timestamp, hr, stress_prob, is_stress):
    """작업자 데이터 업데이트"""
    if len(st.session_state.worker_data[worker_id]) >= DASHBOARD_CONFIG['max_data_points']:
        st.session_state.worker_data[worker_id].pop(0)
    
    st.session_state.worker_data[worker_id].append({
        'timestamp': timestamp,
        'HR': hr,
        'stress_probability': stress_prob,
        'is_stress': is_stress
    })
    
    # 경고 상태 업데이트
    st.session_state.alert_states[worker_id] = is_stress

def create_worker_chart(worker_id, threshold):
    """작업자별 실시간 차트 생성"""
    data = st.session_state.worker_data[worker_id]
    
    if not data:
        return go.Figure()
    
    # 데이터 준비
    timestamps = [d['timestamp'] for d in data]
    hrs = [d['HR'] for d in data]
    stress_probs = [d['stress_probability'] for d in data]
    is_stress_list = [d['is_stress'] for d in data]
    
    # 서브플롯 생성
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=['심박수 (HR)', '스트레스 확률'],
        vertical_spacing=0.15,
        shared_xaxes=True
    )
    
    # 심박수 그래프
    worker_color = WORKERS[worker_id]['color']
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=hrs,
            mode='lines+markers',
            name='심박수',
            line=dict(color=worker_color, width=2),
            marker=dict(size=4)
        ),
        row=1, col=1
    )
    
    # 스트레스 확률 그래프
    stress_colors = [ALERT_CONFIG['stress_color'] if is_stress else ALERT_CONFIG['normal_color'] 
                    for is_stress in is_stress_list]
    
    fig.add_trace(
        go.Scatter(
            x=timestamps, y=stress_probs,
            mode='lines+markers',
            name='스트레스 확률',
            line=dict(color='purple', width=2),
            marker=dict(size=6, color=stress_colors)
        ),
        row=2, col=1
    )
    
    # 임계값 선
    fig.add_hline(
        y=threshold, 
        line_dash="dash", 
        line_color="red",
        annotation_text=f"임계값: {threshold}",
        row=2, col=1
    )
    
    # 레이아웃 설정
    fig.update_layout(
        height=400,
        showlegend=True,
        title=f"{WORKERS[worker_id]['name']} - 실시간 모니터링"
    )
    
    fig.update_xaxes(title_text="시간", row=2, col=1)
    fig.update_yaxes(title_text="BPM", row=1, col=1)
    fig.update_yaxes(title_text="확률", range=[0, 1], row=2, col=1)
    
    return fig

# ===== 메인 대시보드 =====
def main_dashboard():
    """메인 대시보드"""
    
    # 초기화
    initialize_session_state()
    
    # 제목
    st.title(DASHBOARD_CONFIG['page_title'])
    st.markdown("---")
    
    # 사이드바 - 설정
    st.sidebar.header("⚙️ 설정")
    
    # 스트레스 임계값 조정
    threshold = st.sidebar.slider(
        "🎚️ 스트레스 임계값",
        min_value=0.1,
        max_value=0.9,
        value=0.35,
        step=0.05,
        help="이 값보다 높으면 스트레스로 판정됩니다."
    )
    
    # 모드 선택
    st.sidebar.header("📊 데이터 모드")
    mode = st.sidebar.radio(
        "모드 선택:",
        ["🎲 시뮬레이션 데모", "📁 CSV 파일 업로드"],
        help="시뮬레이션 모드에서는 랜덤 데이터를, CSV 모드에서는 실제 데이터를 사용합니다."
    )
    
    # ===== 시뮬레이션 모드 =====
    if mode == "🎲 시뮬레이션 데모":
        st.sidebar.markdown("### 🎬 시뮬레이션 제어")
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("▶️ 시작", key="start_sim"):
                if not st.session_state.is_simulation_running:
                    # 간단한 랜덤 시뮬레이션 시작
                    st.session_state.is_simulation_running = True
                    st.sidebar.success("시뮬레이션 시작!")
                    
                    # 시뮬레이션 데이터 생성
                    import random
                    from datetime import datetime
                    
                    # 실제 개발 모델 사용
                    real_predictor = get_predictor()  # 실제 학습된 모델 로드
                    
                    for worker_id in WORKERS.keys():
                        # 50-150 사이 랜덤 심박수 생성
                        random_hr = random.randint(50, 150)
                        current_time = datetime.now()
                        
                        # 실제 모델 예측
                        result, error = real_predictor.predict_stress_single(random_hr, threshold)
                        
                        if result:
                            # 웹 페이지에 표시할 데이터 업데이트
                            if 'worker_data' in st.session_state:
                                update_worker_data(
                                    worker_id,
                                    current_time,
                                    random_hr,
                                    result['stress_probability'],
                                    result['is_stress']
                                )
                            
                            # 터미널 로그
                            worker_name = WORKERS[worker_id]['name']
                            status = '🚨 스트레스' if result['is_stress'] else '✅ 정상'
                            print(f"🔥 {worker_name}: HR={random_hr}, 스트레스={result['stress_probability']:.3f}, {status}")
                        else:
                            print(f"❌ {WORKERS[worker_id]['name']}: 예측 실패 - {error}")
        
        with col2:
            if st.button("⏹️ 정지", key="stop_sim"):
                if st.session_state.is_simulation_running:
                    st.session_state.simulator.stop_simulation()
                    st.session_state.is_simulation_running = False
                    st.sidebar.info("시뮬레이션 정지!")
    
    # ===== CSV 업로드 모드 =====
    else:
        st.sidebar.markdown("### 📁 CSV 파일 업로드")
        
        for worker_id in WORKERS.keys():
            worker_name = WORKERS[worker_id]['name']
            
            uploaded_file = st.sidebar.file_uploader(
                f"{worker_name} 데이터",
                type=['csv'],
                key=f"upload_{worker_id}",
                help=f"{worker_name}의 심박수 데이터 CSV 파일을 업로드하세요."
            )
            
            if uploaded_file is not None:
                if worker_id not in st.session_state.uploaded_files or \
                   st.session_state.uploaded_files.get(worker_id) != uploaded_file.name:
                    
                    df, error = process_uploaded_csv(uploaded_file, worker_id)
                    
                    if error:
                        st.sidebar.error(f"❌ {worker_name}: {error}")
                    else:
                        st.sidebar.success(f"✅ {worker_name}: {len(df)}개 데이터 로드")
                        st.session_state.uploaded_files[worker_id] = uploaded_file.name
                        
                        # 스트레스 예측 수행
                        result_df, pred_error = st.session_state.predictor.predict_from_dataframe(
                            df, threshold=threshold
                        )
                        
                        if pred_error:
                            st.sidebar.error(f"❌ 예측 실패: {pred_error}")
                        else:
                            # 세션 데이터 업데이트
                            st.session_state.worker_data[worker_id] = []
                            for _, row in result_df.iterrows():
                                update_worker_data(
                                    worker_id,
                                    row['timestamp'],
                                    row['HR'],
                                    row['stress_probability'],
                                    row['is_stress']
                                )
    
    # ===== 메인 컨텐츠 =====
    
    # 전체 상태 요약
    st.header("📊 전체 작업자 상태")
    
    cols = st.columns(4)
    for i, (worker_id, worker_info) in enumerate(WORKERS.items()):
        with cols[i]:
            is_alert = st.session_state.alert_states[worker_id]
            data = st.session_state.worker_data[worker_id]
            
            if data:
                latest_data = data[-1]
                hr = latest_data['HR']
                stress_prob = latest_data['stress_probability']
                
                # 상태에 따른 스타일
                if is_alert:
                    st.markdown(f"""
                    <div style="padding: 10px; border-radius: 10px; 
                                background-color: {ALERT_CONFIG['stress_color']}; 
                                color: white; text-align: center;">
                        <h3>🚨 {worker_info['name']}</h3>
                        <p>HR: {hr} BPM</p>
                        <p>스트레스: {stress_prob:.3f}</p>
                        <p><strong>⚠️ 경고!</strong></p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style="padding: 10px; border-radius: 10px; 
                                background-color: {ALERT_CONFIG['normal_color']}; 
                                color: white; text-align: center;">
                        <h3>✅ {worker_info['name']}</h3>
                        <p>HR: {hr} BPM</p>
                        <p>스트레스: {stress_prob:.3f}</p>
                        <p><strong>정상</strong></p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="padding: 10px; border-radius: 10px; 
                            background-color: #gray; 
                            color: white; text-align: center;">
                    <h3>❓ {worker_info['name']}</h3>
                    <p>데이터 없음</p>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 개별 작업자 차트
    st.header("📈 개별 작업자 모니터링")
    
    for worker_id in WORKERS.keys():
        if st.session_state.worker_data[worker_id]:
            chart = create_worker_chart(worker_id, threshold)
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info(f"{WORKERS[worker_id]['name']}: 데이터가 없습니다.")
    
    # 자동 새로고침 및 연속 시뮬레이션
    if st.session_state.is_simulation_running:
        # 연속 랜덤 데이터 생성
        import random
        from datetime import datetime
        from stress_predictor import StressPredictorEngine
        
        # 실제 개발 모델 사용
        real_predictor = get_predictor()
        
        for worker_id in WORKERS.keys():
            # 50-150 사이 랜덤 심박수 생성
            random_hr = random.randint(50, 150)
            current_time = datetime.now()
            
            # 실제 모델 예측
            result, error = real_predictor.predict_stress_single(random_hr, threshold)
            
            if result:
                # 웹 페이지에 표시할 데이터 업데이트
                if 'worker_data' in st.session_state:
                    update_worker_data(
                        worker_id,
                        current_time,
                        random_hr,
                        result['stress_probability'],
                        result['is_stress']
                    )
        
        time.sleep(DASHBOARD_CONFIG['update_interval'])
        st.rerun()

# ===== 실행 =====
if __name__ == "__main__":
    main_dashboard()
