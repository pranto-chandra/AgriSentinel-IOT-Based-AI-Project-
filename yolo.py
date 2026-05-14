from ultralytics import YOLO
import cv2
import time

model = YOLO("yolov8n.pt")

cap = cv2.VideoCapture(0)
# Give camera time to initialize
time.sleep(2)
# Set camera properties
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

def detect_threat():
    """
    Returns:
        True  - threat detected (person/dog/cow in frame)
        False - safe (no threat objects in frame)
        None  - error or quit signal (camera failed or user pressed 'q')
    """
    # Retry reading frame a few times
    for attempt in range(3):
        ret, frame = cap.read()
        if ret:
            break
        time.sleep(0.1)
    
    if not ret:
        print(f"⚠️ Failed to read frame after 3 attempts")
        return None

    results = model(frame, imgsz=416, conf=0.5)

    threat = False
    
    # Draw bounding boxes on frame
    annotated_frame = frame.copy()
    
    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            label = model.names[cls]
            conf = box.conf[0].item()
            
            # Get box coordinates
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            
            # Check if threat
            if label in ["person", "dog", "cow"]:
                threat = True
                color = (0, 0, 255)  # Red for threat
                thickness = 3
            else:
                color = (0, 255, 0)  # Green for safe
                thickness = 2
            
            # Draw rectangle
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, thickness)
            
            # Draw label with confidence
            text = f"{label} {conf:.2f}"
            cv2.putText(annotated_frame, text, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    # Add threat status to frame
    status_text = "THREAT DETECTED!" if threat else "SAFE"
    status_color = (0, 0, 255) if threat else (0, 255, 0)
    cv2.putText(annotated_frame, status_text, (20, 40), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
    
    # Display frame
    cv2.imshow("AgriSentinel - YOLO Detection", annotated_frame)
    
    # Allow window to be closed or 'q' to quit
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        cv2.destroyAllWindows()
        return None

    return threat


if __name__ == "__main__":
    print("Starting YOLO Detection... Press 'q' to quit")
    
    # Check if camera is available
    if not cap.isOpened():
        print("ERROR: Cannot access camera. Check if it's connected or in use.")
    else:
        print("Camera connected")
        while True:
            result = detect_threat()
            if result is None:
                break
    
    cap.release()
