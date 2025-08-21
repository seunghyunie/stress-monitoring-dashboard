# 🎲 데이터 시뮬레이터 - 4명 작업자 랜덤 데이터 생성
import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta
import time
import threading
from config import WORKERS, SIMULATION_CONFIG

class WorkerDataSimulator:
    """작업자 데이터 시뮬레이션 클래스"""
    
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.worker_name = WORKERS[worker_id]['name']
        
        # 개별 작업자 특성 설정
        self.base_hr = random.randint(*SIMULATION_CONFIG['hr_base_range'])
        self.stress_tendency = random.uniform(0.1, 0.3)  # 스트레스 경향성
        self.current_state = 'normal'  # normal, stress
        self.state_duration = 0
        self.state_start_time = time.time()
        
        # 현재 상태
        self.current_hr = self.base_hr
        self.is_stressed = False
        
    def generate_next_hr(self):
        """다음 심박수 값 생성"""
        current_time = time.time()
        
        # 상태 전환 확인
        if self.current_state == 'normal':
            # 정상 -> 스트레스 전환 체크
            if random.random() < SIMULATION_CONFIG['stress_probability']:
                self.current_state = 'stress'
                self.state_start_time = current_time
                self.state_duration = random.randint(*SIMULATION_CONFIG['stress_duration'])
                
        elif self.current_state == 'stress':
            # 스트레스 지속 시간 체크
            if current_time - self.state_start_time > self.state_duration:
                self.current_state = 'normal'
                self.state_start_time = current_time
        
        # 상태에 따른 심박수 생성
        if self.current_state == 'normal':
            target_hr = self.base_hr + random.randint(-5, 10)
            self.is_stressed = False
        else:  # stress
            stress_min, stress_max = SIMULATION_CONFIG['hr_stress_range']
            target_hr = random.randint(stress_min, stress_max)
            self.is_stressed = True
        
        # 노이즈 추가
        noise = random.randint(-SIMULATION_CONFIG['noise_level'], 
                              SIMULATION_CONFIG['noise_level'])
        target_hr += noise
        
        # 점진적 변화 (급격한 변화 방지)
        diff = target_hr - self.current_hr
        if abs(diff) > 10:
            self.current_hr += diff * 0.3  # 30%씩 점진적 변화
        else:
            self.current_hr = target_hr
        
        # 심박수 범위 제한
        self.current_hr = max(50, min(150, int(self.current_hr)))
        
        return self.current_hr

class MultiWorkerSimulator:
    """4명 작업자 동시 시뮬레이션"""
    
    def __init__(self):
        self.workers = {}
        self.is_running = False
        self.data_callback = None
        self.thread = None
        
        # 작업자 시뮬레이터 초기화
        for worker_id in WORKERS.keys():
            self.workers[worker_id] = WorkerDataSimulator(worker_id)
    
    def set_data_callback(self, callback_func):
        """데이터 업데이트 콜백 함수 설정"""
        self.data_callback = callback_func
    
    def start_simulation(self):
        """시뮬레이션 시작"""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._simulation_loop, daemon=True)
            self.thread.start()
            print("🎬 4명 작업자 시뮬레이션 시작!")
    
    def stop_simulation(self):
        """시뮬레이션 정지"""
        self.is_running = False
        if self.thread:
            self.thread.join()
        print("⏹️ 시뮬레이션 정지!")
    
    def _simulation_loop(self):
        """시뮬레이션 메인 루프"""
        while self.is_running:
            # 현재 시간
            current_time = datetime.now()
            
            # 모든 작업자의 데이터 생성
            worker_data = {}
            for worker_id, simulator in self.workers.items():
                hr = simulator.generate_next_hr()
                worker_data[worker_id] = {
                    'timestamp': current_time,
                    'HR': hr,
                    'worker_name': simulator.worker_name,
                    'is_stressed': simulator.is_stressed,
                    'state': simulator.current_state
                }
            
            # 콜백 함수 호출
            if self.data_callback:
                self.data_callback(worker_data)
            
            # 1초 대기
            time.sleep(1.0)
    
    def get_current_status(self):
        """현재 모든 작업자 상태 반환"""
        status = {}
        for worker_id, simulator in self.workers.items():
            status[worker_id] = {
                'worker_name': simulator.worker_name,
                'current_hr': simulator.current_hr,
                'current_state': simulator.current_state,
                'base_hr': simulator.base_hr,
                'is_stressed': simulator.is_stressed
            }
        return status

def generate_demo_csv_data(worker_id, duration_minutes=10):
    """데모용 CSV 데이터 생성"""
    simulator = WorkerDataSimulator(worker_id)
    
    # 시작 시간
    start_time = datetime.now() - timedelta(minutes=duration_minutes)
    
    data = []
    for i in range(duration_minutes * 60):  # 1초 간격으로 데이터 생성
        timestamp = start_time + timedelta(seconds=i)
        hr = simulator.generate_next_hr()
        
        data.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'HR': hr
        })
    
    df = pd.DataFrame(data)
    return df

def save_demo_csv_files(output_dir='demo_data'):
    """모든 작업자의 데모 CSV 파일 생성"""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    for worker_id in WORKERS.keys():
        worker_name = WORKERS[worker_id]['name']
        df = generate_demo_csv_data(worker_id, duration_minutes=15)
        
        filename = f"{worker_id}_{worker_name.replace(' ', '_')}_demo.csv"
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False)
        print(f"✅ {filepath} 생성 완료 ({len(df)}개 데이터)")

# ===== 테스트 코드 =====
if __name__ == "__main__":
    print("🎲 데이터 시뮬레이터 테스트")
    
    # 1. 단일 작업자 테스트
    print("\n1️⃣ 단일 작업자 시뮬레이션 테스트:")
    worker_sim = WorkerDataSimulator('worker_1')
    
    for i in range(5):
        hr = worker_sim.generate_next_hr()
        print(f"   {i+1}초: HR={hr}, 상태={worker_sim.current_state}")
        time.sleep(1)
    
    # 2. 멀티 작업자 테스트
    print("\n2️⃣ 멀티 작업자 시뮬레이션 테스트:")
    
    def data_callback(worker_data):
        print(f"[{datetime.now().strftime('%H:%M:%S')}]")
        for worker_id, data in worker_data.items():
            print(f"  {data['worker_name']}: HR={data['HR']}, 상태={data['state']}")
    
    multi_sim = MultiWorkerSimulator()
    multi_sim.set_data_callback(data_callback)
    multi_sim.start_simulation()
    
    try:
        time.sleep(10)  # 10초간 시뮬레이션
    except KeyboardInterrupt:
        pass
    finally:
        multi_sim.stop_simulation()
    
    # 3. 데모 CSV 파일 생성
    print("\n3️⃣ 데모 CSV 파일 생성:")
    save_demo_csv_files()
