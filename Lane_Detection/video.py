

import cv2
import numpy as np
import math
import time
from ultralytics import YOLO
import os

class TrafficLightOptimizer:
    def __init__(self):
        self.lane_weights = {
            'left_lane': 1.0,
            'center': 1.2,
            'right_lane': 1.0
        }
        self.min_green_time = 10
        self.max_green_time = 60
        self.yellow_time = 3
        self.current_cycle = 0
        self.history = []
        self.last_light_change = time.time()
        self.current_active_lane = 'left_lane'
        self.current_state = 'green'
        self.state_start_time = time.time()
        
    def calculate_optimal_times(self, lane_counts):
        weighted_counts = {
            lane: count * self.lane_weights[lane] 
            for lane, count in lane_counts.items()
        }
        total_weight = sum(weighted_counts.values())
        
        if total_weight == 0:
            return {lane: self.min_green_time for lane in lane_counts.keys()}
        
        green_times = {}
        for lane in lane_counts:
            proportion = weighted_counts[lane] / total_weight
            green_time = self.min_green_time + proportion * (self.max_green_time - self.min_green_time)
            green_times[lane] = min(self.max_green_time, max(self.min_green_time, round(green_time)))
        
        return green_times
    
    def get_next_state(self, lane_counts):
        current_time = time.time()
        state_duration = current_time - self.state_start_time
        
        optimal_times = self.calculate_optimal_times(lane_counts)
        
        if self.current_state == 'green':
            if state_duration >= optimal_times[self.current_active_lane]:
                self.current_state = 'yellow'
                self.state_start_time = current_time
                return f"{self.current_active_lane} switching to yellow"
        
        elif self.current_state == 'yellow':
            if state_duration >= self.yellow_time:
                self.current_state = 'red'
                if self.current_active_lane == 'left_lane':
                    self.current_active_lane = 'center'
                elif self.current_active_lane == 'center':
                    self.current_active_lane = 'right_lane'
                else:
                    self.current_active_lane = 'left_lane'
                self.state_start_time = current_time
                return f"Switching to {self.current_active_lane} green"
        
        elif self.current_state == 'red':
            self.current_state = 'green'
            self.state_start_time = current_time
            return f"{self.current_active_lane} now green for {optimal_times[self.current_active_lane]}s"
        
        return f"{self.current_active_lane} {self.current_state} ({int(optimal_times[self.current_active_lane] - state_duration)}s remaining)"

def region_of_interest(img, vertices):
    mask = np.zeros_like(img)
    match_mask_color = 255
    cv2.fillPoly(mask, vertices, match_mask_color)
    masked_image = cv2.bitwise_and(img, mask)
    return masked_image

def draw_lane_lines(img, left_line, right_line, color=[0, 0, 0], thickness=10):
    line_img = np.zeros_like(img)
    poly_pts = np.array([[
        (left_line[0], left_line[1]),
        (left_line[2], left_line[3]),
        (right_line[2], right_line[3]),
        (right_line[0], right_line[1])
    ]], dtype=np.int32)
    
    cv2.fillPoly(line_img, poly_pts, color)
    img = cv2.addWeighted(img, 0.8, line_img, 0.5, 0.0)
    return img

def pipeline(image):
    height = image.shape[0]
    width = image.shape[1]
    region_of_interest_vertices = [
        (0, height),
        (width // 2, height // 2),
        (width, height),
    ]

    gray_image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    cannyed_image = cv2.Canny(gray_image, 100, 200)

    cropped_image = region_of_interest(
        cannyed_image,
        np.array([region_of_interest_vertices], np.int32)
    )

    lines = cv2.HoughLinesP(
        cropped_image,
        rho=6,
        theta=np.pi / 60,
        threshold=160,
        lines=np.array([]),
        minLineLength=40,
        maxLineGap=25
    )

    left_line_x = []
    left_line_y = []
    right_line_x = []
    right_line_y = []

    if lines is None:
        return image

    for line in lines:
        for x1, y1, x2, y2 in line:
            slope = (y2 - y1) / (x2 - x1) if (x2 - x1) != 0 else 0
            if math.fabs(slope) < 0.5:
                continue
            if slope <= 0:
                left_line_x.extend([x1, x2])
                left_line_y.extend([y1, y2])
            else:
                right_line_x.extend([x1, x2])
                right_line_y.extend([y1, y2])

    min_y = int(image.shape[0] * (3 / 5))
    max_y = image.shape[0]

    if left_line_x and left_line_y:
        poly_left = np.poly1d(np.polyfit(left_line_y, left_line_x, deg=1))
        left_x_start = int(poly_left(max_y))
        left_x_end = int(poly_left(min_y))
    else:
        left_x_start, left_x_end = 0, 0

    if right_line_x and right_line_y:
        poly_right = np.poly1d(np.polyfit(right_line_y, right_line_x, deg=1))
        right_x_start = int(poly_right(max_y))
        right_x_end = int(poly_right(min_y))
    else:
        right_x_start, right_x_end = 0, 0

    lane_image = draw_lane_lines(
        image,
        [left_x_start, max_y, left_x_end, min_y],
        [right_x_start, max_y, right_x_end, min_y]
    )

    return lane_image

def estimate_distance(bbox_width):
    focal_length = 1000
    known_width = 2.0
    distance = (known_width * focal_length) / bbox_width
    return distance

def process_video():
    model = YOLO('yolov8n.pt')
    cap = cv2.VideoCapture('D:/NextNiche Hackathon/TestF/Lane_Detection/video/car2.mp4')
    
    if not cap.isOpened():
        print("Error: Unable to open video file.")
        return

    # Create output directory if it doesn't exist
    os.makedirs('output', exist_ok=True)

    optimizer = TrafficLightOptimizer()
    frame_count = 0
    output_data = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        resized_frame = cv2.resize(frame, (1280, 720))
        height, width = resized_frame.shape[:2]
        lane_frame = pipeline(resized_frame)

        lane_counts = {
            'left_lane': 0,
            'center': 0,
            'right_lane': 0
        }

        results = model(resized_frame)
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = box.conf[0]
                cls = int(box.cls[0])

                if model.names[cls] == 'car' and conf >= 0.5:
                    car_center_x = (x1 + x2) / 2
                    if car_center_x < width / 3:
                        current_lane = 'left_lane'
                    elif car_center_x > 2 * width / 3:
                        current_lane = 'right_lane'
                    else:
                        current_lane = 'center'
                    
                    lane_counts[current_lane] += 1

                    cv2.rectangle(lane_frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                    cv2.putText(lane_frame, f'Car {conf:.2f}', (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

                    distance = estimate_distance(x2 - x1)
                    cv2.putText(lane_frame, f'{distance:.2f}m', (x1, y2 + 20),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        status = optimizer.get_next_state(lane_counts)
        optimal_times = optimizer.calculate_optimal_times(lane_counts)

        # Display traffic information
        cv2.putText(lane_frame, f"Left Lane: {lane_counts['left_lane']} cars", (20, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(lane_frame, f"Center Lane: {lane_counts['center']} cars", (20, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(lane_frame, f"Right Lane: {lane_counts['right_lane']} cars", (20, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.putText(lane_frame, f"Current: {status}", (20, 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv2.putText(lane_frame, "Optimal Green Times:", (width - 350, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(lane_frame, f"Left: {optimal_times['left_lane']}s", (width - 350, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(lane_frame, f"Center: {optimal_times['center']}s", (width - 350, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(lane_frame, f"Right: {optimal_times['right_lane']}s", (width - 350, 130),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        output_data.append({
            'frame': frame_count,
            'left_count': lane_counts['left_lane'],
            'center_count': lane_counts['center'],
            'right_count': lane_counts['right_lane'],
            'left_green': optimal_times['left_lane'],
            'center_green': optimal_times['center'],
            'right_green': optimal_times['right_lane'],
            'current_status': status
        })

        cv2.imwrite(f'output/frame_.jpg', lane_frame)
        frame_count += 1

        # Control processing speed without waitKey
        time.sleep(0.03)  # ~30fps

    cap.release()
    
    print("\nTraffic Light Optimization Results:")
    print("Frame | Left (Count/Time) | Center (Count/Time) | Right (Count/Time) | Status")
    for data in output_data[-10:]:
        print(f"{data['frame']:5} | "
              f"{data['left_count']:3} / {data['left_green']:3}s | "
              f"{data['center_count']:3} / {data['center_green']:3}s | "
              f"{data['right_count']:3} / {data['right_green']:3}s | "
              f"{data['current_status']}")

process_video()