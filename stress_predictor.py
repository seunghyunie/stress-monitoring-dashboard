# 🔮 스트레스 예측 엔진
import numpy as np
import pandas as pd
from tensorflow.keras.models import load_model
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

from config import MODEL_CONFIG

class StressPredictorEngine:
    """스트레스 예측을 위한 메인 엔진"""
    
    def __init__(self):
        self.hrv_model = None
        self.stress_model = None
        self.is_loaded = False
        self.scaler = StandardScaler()
        
    def load_models(self):
        """모델 로드"""
        try:
            print("🔄 모델 로딩 중...")
            
            # 모델 파일 존재 확인
            import os
            hrv_path = MODEL_CONFIG["hrv_model_path"]
            stress_path = MODEL_CONFIG["stress_model_path"]
            
            if not os.path.exists(hrv_path):
                raise FileNotFoundError(f"HRV 모델 파일을 찾을 수 없습니다: {hrv_path}")
            if not os.path.exists(stress_path):
                raise FileNotFoundError(f"스트레스 모델 파일을 찾을 수 없습니다: {stress_path}")
            
            # 모델 로드
            self.hrv_model = load_model(hrv_path)
            self.stress_model = load_model(stress_path)
            
            self.is_loaded = True
            print("✅ 모델 로딩 완료!")
            return True
            
        except Exception as e:
            print(f"❌ 모델 로딩 실패: {e}")
            print("🎲 시뮬레이션 모드로 동작합니다 (실제 모델 없음)")
            self.is_loaded = False
            return False
    
    def predict_stress_single(self, hr_value, threshold=None):
        """단일 HR 값으로 스트레스 예측"""
        if not self.is_loaded:
            # 모델이 없을 때 시뮬레이션 모드로 동작
            return self._simulate_prediction(hr_value, threshold)
        
        try:
            # HR 데이터 전처리 - 다양한 정규화 방식 시도
            # 방법 1: 단순 스케일링 (0-1)
            hr_scaled_01 = (hr_value - 30) / (200 - 30)  # 30-200 BPM → 0-1
            
            # 방법 2: 표준화 (평균 75, 표준편차 20)
            hr_standardized = (hr_value - 75) / 20
            
            # 방법 3: 원본 값 사용
            hr_original = hr_value
            
            # 모델에 따라 다른 전처리 시도 (여러 방법 테스트)
            hr_array = np.array([[hr_scaled_01]])  # 먼저 0-1 스케일링 시도
            
            # HRV 예측 (HR → HRV)
            hr_seq = hr_array.reshape(-1, 1, 1)
            hrv_pred = self.hrv_model.predict(hr_seq, verbose=0)
            
            # 스트레스 예측 ([HR, HRV] → 스트레스 확률)
            stress_input = np.concatenate([hr_array, hrv_pred], axis=1)
            stress_prob = self.stress_model.predict(stress_input, verbose=0)[0][0]
            
            print(f"🔍 모델 예측 상세:")
            print(f"   입력 HR: {hr_value} → 정규화: {hr_array[0]}")
            print(f"   HRV 예측: {hrv_pred[0]}")
            print(f"   스트레스 입력: {stress_input[0]}")
            print(f"   스트레스 확률: {stress_prob:.6f}")
            
            # 임계값 적용
            if threshold is None:
                threshold = MODEL_CONFIG['default_threshold']
            
            is_stress = stress_prob >= threshold
            
            return {
                'hr': hr_value,
                'stress_probability': float(stress_prob),
                'is_stress': bool(is_stress),
                'threshold': threshold,
                'status': 'stress' if is_stress else 'normal'
            }, None
            
        except Exception as e:
            return None, f"예측 오류: {e}"
    
    def _simulate_prediction(self, hr_value, threshold=None):
        """모델이 없을 때 HR 기반 시뮬레이션 예측"""
        try:
            # 임계값 설정
            if threshold is None:
                threshold = MODEL_CONFIG['default_threshold']
            
            # 더 다양한 스트레스 확률 계산
            # 기본 확률을 HR에 따라 설정
            if hr_value < 60:
                # 너무 낮은 심박수 - 브래디카디아
                base_prob = 0.6 + (60 - hr_value) * 0.01
            elif hr_value <= 70:
                # 낮은 정상 범위
                base_prob = 0.05 + np.random.uniform(0, 0.15)
            elif hr_value <= 90:
                # 정상 범위
                base_prob = 0.1 + np.random.uniform(0, 0.25)
            elif hr_value <= 110:
                # 약간 높은 범위
                base_prob = 0.3 + (hr_value - 90) * 0.015 + np.random.uniform(0, 0.3)
            elif hr_value <= 130:
                # 높은 범위
                base_prob = 0.5 + (hr_value - 110) * 0.02 + np.random.uniform(0, 0.2)
            else:
                # 매우 높은 심박수 - 타키카디아
                base_prob = 0.7 + min(0.25, (hr_value - 130) * 0.01) + np.random.uniform(0, 0.15)
            
            # 추가 랜덤 변동성
            noise = np.random.normal(0, 0.1)
            stress_prob = base_prob + noise
            
            # 확률 범위 제한 (0-1)
            stress_prob = max(0.0, min(1.0, stress_prob))
            
            is_stress = stress_prob >= threshold
            
            return {
                'hr': hr_value,
                'stress_probability': float(stress_prob),
                'is_stress': bool(is_stress),
                'threshold': threshold,
                'status': 'stress' if is_stress else 'normal'
            }, None
            
        except Exception as e:
            return None, f"시뮬레이션 오류: {e}"
    
    def predict_stress_batch(self, hr_values, threshold=None):
        """여러 HR 값들을 배치로 스트레스 예측"""
        # 모델이 로드되지 않았어도 시뮬레이션으로 동작
        
        results = []
        for hr in hr_values:
            result, error = self.predict_stress_single(hr, threshold)
            if result:
                results.append(result)
            else:
                # 오류 발생 시 기본값
                results.append({
                    'hr': hr,
                    'stress_probability': 0.0,
                    'is_stress': False,
                    'threshold': threshold or MODEL_CONFIG['default_threshold'],
                    'status': 'error'
                })
        
        return results, None
    
    def predict_from_dataframe(self, df, hr_column='HR', threshold=None):
        """DataFrame에서 HR 데이터를 읽어 스트레스 예측"""
        try:
            if hr_column not in df.columns:
                return None, f"컬럼 '{hr_column}'을 찾을 수 없습니다"
            
            hr_values = df[hr_column].tolist()
            results, error = self.predict_stress_batch(hr_values, threshold)
            
            if error:
                return None, error
            
            # 결과를 DataFrame에 추가
            result_df = df.copy()
            result_df['stress_probability'] = [r['stress_probability'] for r in results]
            result_df['is_stress'] = [r['is_stress'] for r in results]
            result_df['status'] = [r['status'] for r in results]
            
            return result_df, None
            
        except Exception as e:
            return None, f"DataFrame 처리 오류: {e}"

# 전역 예측 엔진 인스턴스
_predictor_instance = None

def get_predictor():
    """예측 엔진 싱글톤 인스턴스 반환"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = StressPredictorEngine()
        _predictor_instance.load_models()
    return _predictor_instance

def quick_predict(hr_value, threshold=None):
    """빠른 스트레스 예측 (단일 값)"""
    predictor = get_predictor()
    return predictor.predict_stress_single(hr_value, threshold)

# ===== 테스트 코드 =====
if __name__ == "__main__":
    # 예측 엔진 테스트
    print("🧪 스트레스 예측 엔진 테스트")
    
    predictor = StressPredictorEngine()
    
    if predictor.load_models():
        # 단일 값 테스트
        test_hr = 85
        result, error = predictor.predict_stress_single(test_hr)
        
        if result:
            print(f"✅ 테스트 성공!")
            print(f"   HR: {result['hr']}")
            print(f"   스트레스 확률: {result['stress_probability']:.3f}")
            print(f"   스트레스 여부: {result['is_stress']}")
        else:
            print(f"❌ 테스트 실패: {error}")
    else:
        print("❌ 모델 로드 실패")
