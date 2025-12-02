/*
 * 무선전력 충전 시스템 (XY Stage Auto-Align & Charging)
 * 최종 통합본 (Final Version)
 */

#include <Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ==========================================
// 1. 하드웨어 설정
// ==========================================
LiquidCrystal_I2C lcd(0x27, 16, 2); // 주소: 0x27 or 0x3F

const int PIN_LED_R = 11;
const int PIN_LED_O = 12;
const int PIN_LED_G = 13;

const int PIN_SERVO_X = 9;
const int PIN_SERVO_Y = 10;

const int TRIG_L = 4, ECHO_L = 5; // X축 거리 측정용
const int TRIG_R = 6, ECHO_R = 7; // (보조)
const int TRIG_F = 2, ECHO_F = 3; // Y축 거리 측정용

const int PIN_CURRENT = A0;

Servo servoX;
Servo servoY;

// ==========================================
// 2. 캘리브레이션 변수 (★나중에 여기를 수정하세요★)
// ==========================================

// ---------------------------------------------------------
// <<< [수정할 부분 시작] >>>
// 캘리브레이션 도구로 구한 값을 여기에 넣으세요.
// 공식: 각도 = (AX * 거리) + BX

// [X축 설정]
float AX = 1.0;    // 기울기 (예: 5.33)
float BX = 0.0;    // 절편 (예: -70.0)

// [Y축 설정]
float AY = 1.0;    // 기울기 (예: -5.33)
float BY = 0.0;    // 절편 (예: 276.5)

// [서보 안전 범위] (기계적으로 닿지 않는 안전 각도)
const int SERVO_MIN = 10;  
const int SERVO_MAX = 170; 
// <<< [수정할 부분 끝] >>>
// ---------------------------------------------------------

// 서보 홈 위치
const int X_HOME = 90;   
const int Y_HOME = 90;   
const int T_SERVO_WAIT = 1000; // 이동 후 대기 시간

// ==========================================
// 3. 시스템 변수 정의
// ==========================================
enum State {
  S00_WAIT_SIGNAL, 
  S01_WAIT_INPUT,  
  S1_APPROVING,
  S2_APPROVED,
  S3_ALIGNING,
  S4_CHARGING,
  S5_COMPLETED
};
State currentState = S00_WAIT_SIGNAL;
bool isStateFirstRun = true; // 상태 진입 플래그

// 충전 변수
float Q_target_mAh = 0.0;
double Q_accum_As = 0.0;
double Q_accum_mAh = 0.0;
unsigned long lastCurrentMeasureTime = 0;

// UI 변수
unsigned long stateStartTime = 0;
unsigned long lastScreenSwitch = 0;
int screenMode = 1;   
int lastAnimSec = -1; 

// ==========================================
// 4. 초기화 (Setup)
// ==========================================
void setup() {
  Serial.begin(9600);
  lcd.init(); lcd.backlight();
  
  pinMode(PIN_LED_R, OUTPUT);
  pinMode(PIN_LED_O, OUTPUT);
  pinMode(PIN_LED_G, OUTPUT);
  
  pinMode(TRIG_L, OUTPUT); pinMode(ECHO_L, INPUT);
  pinMode(TRIG_R, OUTPUT); pinMode(ECHO_R, INPUT);
  pinMode(TRIG_F, OUTPUT); pinMode(ECHO_F, INPUT);
  
  servoX.attach(PIN_SERVO_X);
  servoY.attach(PIN_SERVO_Y);
  
  lcd.setCursor(0, 0); lcd.print("SYSTEM BOOT...");
  resetSystem(); 
}

// ==========================================
// 5. 메인 루프
// ==========================================
void loop() {
  switch (currentState) {
    case S00_WAIT_SIGNAL: handle_S00_WaitSignal(); break;
    case S01_WAIT_INPUT:  handle_S01_WaitInput();  break;
    case S1_APPROVING:    handle_S1_Approving();   break;
    case S2_APPROVED:     handle_S2_Approved();    break;
    case S3_ALIGNING:     handle_S3_Aligning();    break;
    case S4_CHARGING:     handle_S4_Charging();    break;
    case S5_COMPLETED:    handle_S5_Completed();   break;
  }
}

// ==========================================
// 6. 상태 제어 함수
// ==========================================
void changeState(State newState) {
  currentState = newState;
  stateStartTime = millis();
  isStateFirstRun = true; 
  lastAnimSec = -1;
  lastScreenSwitch = 0; 
  screenMode = 1; 
  lcd.clear();
}

void resetSystem() {
  digitalWrite(PIN_LED_R, LOW);
  digitalWrite(PIN_LED_O, LOW);
  digitalWrite(PIN_LED_G, LOW);
  
  // 서보 원위치 이동
  servoX.write(X_HOME); delay(800);
  servoY.write(Y_HOME); delay(800);

  Q_accum_As = 0; Q_accum_mAh = 0; Q_target_mAh = 0;
  changeState(S00_WAIT_SIGNAL);
}

// ==========================================
// 7. 상태별 상세 동작
// ==========================================

// S00: 차량 감지 대기
void handle_S00_WaitSignal() {
  if (isStateFirstRun) {
    lcd.setCursor(0, 0); lcd.print("WAITING SIGNAL..");
    lcd.setCursor(0, 1); lcd.print("Ready to Detect");
    Serial.println("\n[S00] 차량 감지 대기중... (아무 키나 누르세요)");
    while(Serial.available()) Serial.read();
    isStateFirstRun = false;
  }
  if (Serial.available() > 0) {
    while(Serial.available()) Serial.read();
    Serial.println(">> 차량 인식됨!");
    changeState(S01_WAIT_INPUT);
  }
}

// S01: 입력 대기
void handle_S01_WaitInput() {
  if (isStateFirstRun) {
    lcd.setCursor(0, 0); lcd.print("VEHICLE DETECTED");
    lcd.setCursor(0, 1); lcd.print("Input Target Q");
    Serial.println("\n[S01] 목표 충전량(mAh) 입력 (0=디버깅):");
    isStateFirstRun = false;
  }
  if (Serial.available() > 0) {
    float inputVal = Serial.parseFloat();
    while(Serial.available()) Serial.read(); 
    if (inputVal < 0) inputVal = 0;
    Q_target_mAh = inputVal;
    
    Serial.print(">> 설정된 목표량: "); Serial.print((int)Q_target_mAh); Serial.println(" mAh");
    changeState(S1_APPROVING);
  }
}

// S1: 승인 (10초)
void handle_S1_Approving() {
  if (isStateFirstRun) {
    digitalWrite(PIN_LED_R, HIGH);
    Serial.println("\n[S1] 승인 중...");
    isStateFirstRun = false;
  }
  int elapsedSec = (millis() - stateStartTime) / 1000;
  if (elapsedSec >= 10) {
    digitalWrite(PIN_LED_R, LOW);
    changeState(S2_APPROVED);
    return;
  }
  if (elapsedSec != lastAnimSec) {
    lastAnimSec = elapsedSec;
    lcd.clear();
    lcd.setCursor(0, 0); lcd.print("APPROVING");
    for (int i = 0; i < (elapsedSec % 4); i++) lcd.print(".");
    lcd.setCursor(0, 1); lcd.print("Please Wait "); lcd.print(10 - elapsedSec); lcd.print("s");
  }
}

// S2: 승인 완료 (5초)
void handle_S2_Approved() {
  if (isStateFirstRun) {
    digitalWrite(PIN_LED_G, HIGH);
    lcd.setCursor(0, 0); lcd.print("APPROVED!");
    lcd.setCursor(0, 1); lcd.print("Ready to Align");
    Serial.println("\n[S2] 승인 완료.");
    isStateFirstRun = false;
  }
  if (millis() - stateStartTime >= 5000) {
    digitalWrite(PIN_LED_G, LOW);
    changeState(S3_ALIGNING);
  }
}

// S3: 정렬 (핵심 로직)
void handle_S3_Aligning() {
  if (isStateFirstRun) {
     Serial.println("\n[S3] 정렬 시작...");
     isStateFirstRun = false;
  }

  // [1] X축 정렬
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print("MEASURING X...");
  float distL = getDistance(TRIG_L, ECHO_L);
  
  // 좌표 변환 공식 적용
  int thetaX = (int)(AX * distL + BX);
  // 안전 범위 제한 (매우 중요)
  thetaX = constrain(thetaX, SERVO_MIN, SERVO_MAX);
  
  lcd.setCursor(0, 1); lcd.print("Moving X...");
  servoX.write(thetaX);
  delay(T_SERVO_WAIT);
  
  // [2] Y축 정렬
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print("MEASURING Y...");
  float distF = getDistance(TRIG_F, ECHO_F);
  
  int thetaY = (int)(AY * distF + BY);
  thetaY = constrain(thetaY, SERVO_MIN, SERVO_MAX);
  
  lcd.setCursor(0, 1); lcd.print("Moving Y...");
  servoY.write(thetaY);
  delay(T_SERVO_WAIT);
  
  // [3] 완료 대기 (5초)
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print("ALIGN COMPLETE");
  Serial.println(">> 정렬 완료. 5초 후 충전.");
  delay(5000); 
  
  lastCurrentMeasureTime = millis(); 
  changeState(S4_CHARGING);
}

// S4: 충전
void handle_S4_Charging() {
  if (isStateFirstRun) {
    digitalWrite(PIN_LED_O, HIGH);
    Serial.println("\n[S4] 충전 시작.");
    isStateFirstRun = false;
  }
  unsigned long currentMillis = millis();
  double dt = (currentMillis - lastCurrentMeasureTime) / 1000.0;
  lastCurrentMeasureTime = currentMillis;
  
  float currentAmps = readCurrentSensor();
  Q_accum_As += currentAmps * dt;
  Q_accum_mAh = Q_accum_As / 3.6;
  
  if (currentMillis - lastScreenSwitch > 3000) {
    lastScreenSwitch = currentMillis;
    screenMode = !screenMode;
    lcd.clear();
    if (screenMode == 0) {
      lcd.setCursor(0, 0); lcd.print("CHARGING...");
      lcd.setCursor(0, 1);
      if (Q_target_mAh == 0) lcd.print("[DEBUG MODE]"); else lcd.print("Do Not Touch");
    } else {
      lcd.setCursor(0, 0); lcd.print("Tgt:"); lcd.print((int)Q_target_mAh); lcd.print("mA");
      lcd.setCursor(0, 1); lcd.print("Cur:"); lcd.print((int)Q_accum_mAh); lcd.print("mA");
    }
    Serial.print("I: "); Serial.print(currentAmps); Serial.print(" A | Q: "); Serial.println(Q_accum_mAh);
  }
  
  bool isFinished = false;
  if (Q_target_mAh == 0) { // 디버깅
    if (millis() - stateStartTime >= 10000) isFinished = true;
  } else { // 정상
    if (Q_accum_mAh >= Q_target_mAh) isFinished = true;
  }
  
  if (isFinished) {
    digitalWrite(PIN_LED_O, LOW);
    changeState(S5_COMPLETED);
  }
}

// S5: 완료
void handle_S5_Completed() {
  if (isStateFirstRun) {
    digitalWrite(PIN_LED_G, HIGH);
    lcd.setCursor(0, 0); lcd.print("CHARGE COMPLETE!");
    lcd.setCursor(0, 1); lcd.print("Returning...");
    Serial.println("\n[S5] 충전 완료. 복귀 중...");
    isStateFirstRun = false;
  }
  if (millis() - stateStartTime > 2000) {
    servoX.write(X_HOME); delay(T_SERVO_WAIT);
    servoY.write(Y_HOME); delay(T_SERVO_WAIT);
    delay(5000);
    resetSystem();
  }
}

// ==========================================
// 8. 센서 보조 함수
// ==========================================
float getDistance(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW); delayMicroseconds(2);
  digitalWrite(trigPin, HIGH); delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long duration = pulseIn(echoPin, HIGH, 30000);
  if (duration == 0) return 999.0;
  return duration * 0.034 / 2;
}

float readCurrentSensor() {
  int raw = analogRead(PIN_CURRENT);
  float voltage = (raw / 1023.0) * 5.0;
  // 센서 영점(2.5V) 미세 조정 필요 시 2.5를 변경하세요.
  float amps = (voltage - 2.5) / 0.185; 
  return abs(amps);
}