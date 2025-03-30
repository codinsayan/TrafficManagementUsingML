import pygame
import random
import math
import time
from collections import defaultdict

# Initialize pygame
pygame.init()
screen_width, screen_height = 1366, 768
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("6-Way Smart Intersection Simulation with Synchronized Opposite Lanes")
clock = pygame.time.Clock()

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 50, 50)
YELLOW = (255, 255, 0)
GREEN = (50, 255, 50)
GRAY = (120, 120, 120)
ROAD_COLOR = (70, 70, 70)

# Vehicle types with different properties
VEHICLE_TYPES = {
    'car': {'width': 28, 'height': 14, 'color': (0, 150, 255), 'speed': (2.5, 4.5)},
    'bus': {'width': 36, 'height': 18, 'color': (255, 120, 0), 'speed': (2, 3.5)},
    'truck': {'width': 40, 'height': 22, 'color': (180, 80, 0), 'speed': (1.5, 3)},
    'motorcycle': {'width': 22, 'height': 10, 'color': (255, 255, 100), 'speed': (3.5, 6)}
}

# Font settings
FONT_LARGE = pygame.font.SysFont('Arial', 24, bold=True)
FONT_MEDIUM = pygame.font.SysFont('Arial', 20)
FONT_SMALL = pygame.font.SysFont('Arial', 16)

class TrafficLightOptimizer:
    def __init__(self, roads):
        self.roads = roads
        self.min_green_time = 12
        self.max_green_time = 50
        self.yellow_time = 4
        self.current_phase = 0
        self.phases = self.generate_phases()
        self.current_state = 'red'
        self.state_start_time = time.time()
        self.weights = {road: 1.0 for road in roads}
        self.weights['road1'] = 1.3
        self.weights['road4'] = 1.2
        self.optimal_times = {road: self.min_green_time for road in roads}
        
    def generate_phases(self):
        # Each phase controls opposite directions simultaneously
        return [
            ['road1_in', 'road4_out', 'road4_in', 'road1_out'],  # Phase 0: Road1 and Road4 both directions
            ['road2_in', 'road5_out', 'road5_in', 'road2_out'],  # Phase 1: Road2 and Road5 both directions
            ['road3_in', 'road6_out', 'road6_in', 'road3_out']   # Phase 2: Road3 and Road6 both directions
        ]
    
    def calculate_optimal_times(self, vehicle_counts):
        total_weighted_vehicles = sum(count * self.weights.get(road[:-3], 1.0) 
                                    for road, count in vehicle_counts.items())
        
        if total_weighted_vehicles < 2:
            return {road: self.min_green_time for road in self.phases[self.current_phase]}
        
        green_times = {}
        current_phase_roads = self.phases[self.current_phase]
        
        for road in current_phase_roads:
            base_road = road[:-3]  # Remove direction suffix
            proportion = (vehicle_counts[road] * self.weights.get(base_road, 1.0)) / total_weighted_vehicles
            green_time = self.min_green_time + proportion * (self.max_green_time - self.min_green_time)
            green_times[road] = min(self.max_green_time, max(self.min_green_time, round(green_time)))
        
        return green_times
    
    def update_phase(self, vehicle_counts):
        current_time = time.time()
        state_duration = current_time - self.state_start_time
        
        if self.current_state == 'green':
            self.optimal_times = self.calculate_optimal_times(vehicle_counts)
            avg_green_time = sum(self.optimal_times.values()) / len(self.optimal_times)
            
            if state_duration >= avg_green_time:
                self.current_state = 'yellow'
                self.state_start_time = current_time
                return "Switching to YELLOW"
        
        elif self.current_state == 'yellow':
            if state_duration >= self.yellow_time:
                self.current_state = 'red'
                self.state_start_time = current_time
                self.current_phase = (self.current_phase + 1) % len(self.phases)
                return f"Switching to PHASE {self.current_phase}"
        
        elif self.current_state == 'red':
            if state_duration >= 1.5:
                self.current_state = 'green'
                self.state_start_time = current_time
                return f"PHASE {self.current_phase} GREEN"
        
        return f"PHASE {self.current_phase} {self.current_state.upper()}"

class Vehicle:
    def __init__(self, road, lane, direction):
        self.road = road
        self.lane = lane  # 0 (left lane) or 1 (right lane)
        self.direction = direction  # 'in' or 'out'
        self.type = random.choice(list(VEHICLE_TYPES.keys()))
        self.speed = random.uniform(*VEHICLE_TYPES[self.type]['speed'])
        self.width = VEHICLE_TYPES[self.type]['width']
        self.height = VEHICLE_TYPES[self.type]['height']
        self.color = VEHICLE_TYPES[self.type]['color']
        self.x, self.y = self.get_initial_position()
        self.waiting_time = 0
        self.passed_intersection = False
        
    def get_initial_position(self):
        road_num = int(self.road[-1])
        angle = math.radians((road_num - 1) * 60)
        
        # Different spawn distances based on direction
        spawn_dist = 500 if self.direction == 'in' else 200
        
        # Lane offsets (left lane closer to center for incoming, opposite for outgoing)
        if self.direction == 'in':
            lane_offset = 25 if self.lane == 0 else -25
        else:
            lane_offset = -25 if self.lane == 0 else 25
        
        # Calculate position
        x = screen_width//2 + math.cos(angle) * spawn_dist
        y = screen_height//2 + math.sin(angle) * spawn_dist
        
        # Adjust for lane position
        x += math.cos(angle + math.pi/2) * lane_offset
        y += math.sin(angle + math.pi/2) * lane_offset
        
        return x, y
    
    def update(self, optimizer):
        in_intersection = self.is_in_intersection()
        should_stop = False
        
        # Check if vehicle needs to stop at intersection
        if in_intersection and not self.passed_intersection:
            road_key = f"{self.road}_{self.direction}"
            active_roads = optimizer.phases[optimizer.current_phase]
            if optimizer.current_state != 'green' or road_key not in active_roads:
                should_stop = True
                self.waiting_time += 1
            else:
                self.passed_intersection = True
        
        if not should_stop:
            self.move_vehicle()
        
        # Reset if vehicle goes off screen
        if self.is_off_screen():
            self.reset_vehicle()
    
    def move_vehicle(self):
        road_num = int(self.road[-1])
        angle = math.radians((road_num - 1) * 60)
        move_x = math.cos(angle) * self.speed
        move_y = math.sin(angle) * self.speed
        
        if self.direction == 'in':
            self.x -= move_x
            self.y -= move_y
        else:
            self.x += move_x
            self.y += move_y
    
    def is_in_intersection(self):
        distance = math.sqrt((self.x - screen_width//2)**2 + (self.y - screen_height//2)**2)
        return distance < 150
    
    def is_off_screen(self):
        return (self.x < -200 or self.x > screen_width + 200 or 
                self.y < -200 or self.y > screen_height + 200)
    
    def reset_vehicle(self):
        # 50% chance to spawn a new vehicle going the opposite direction
        if random.random() < 0.5:
            self.direction = 'out' if self.direction == 'in' else 'in'
        self.__init__(self.road, random.randint(0, 1), self.direction)
    
    def draw(self, screen):
        road_num = int(self.road[-1])
        angle = math.radians((road_num - 1) * 60)
        
        if self.direction == 'out':
            angle += math.pi
        
        # Draw vehicle with proper rotation
        vehicle_surface = pygame.Surface((self.width+4, self.height+4), pygame.SRCALPHA)
        pygame.draw.rect(vehicle_surface, self.color, (2, 2, self.width, self.height))
        pygame.draw.rect(vehicle_surface, BLACK, (2, 2, self.width, self.height), 1)
        
        rotated_vehicle = pygame.transform.rotate(vehicle_surface, -math.degrees(angle))
        rect = rotated_vehicle.get_rect(center=(self.x, self.y))
        screen.blit(rotated_vehicle, rect.topleft)

def draw_intersection(screen, optimizer):
    # Draw the circular intersection center
    pygame.draw.circle(screen, ROAD_COLOR, (screen_width//2, screen_height//2), 150)
    pygame.draw.circle(screen, (100, 100, 100), (screen_width//2, screen_height//2), 150, 3)
    
    # Draw 6 roads with proper bidirectional lanes
    for i in range(1, 7):
        angle = math.radians((i-1) * 60)
        
        # Draw lanes for each direction
        for direction in ['in', 'out']:
            start_x = screen_width//2 + math.cos(angle) * 150
            start_y = screen_height//2 + math.sin(angle) * 150
            end_x = screen_width//2 + math.cos(angle) * (500 if direction == 'in' else -200)
            end_y = screen_height//2 + math.sin(angle) * (500 if direction == 'in' else -200)
            
            # Two lanes per direction
            for lane in [0, 1]:
                lane_offset = 25 if lane == 0 else -25
                offset_x = math.cos(angle + math.pi/2) * lane_offset
                offset_y = math.sin(angle + math.pi/2) * lane_offset
                
                # Draw road lane
                lane_width = 15
                pygame.draw.line(screen, ROAD_COLOR, 
                                (start_x + offset_x, start_y + offset_y),
                                (end_x + offset_x, end_y + offset_y), 
                                lane_width)
                
                # Draw lane markers (skip near intersection)
                marker_spacing = 40
                marker_length = 10
                for dist in range(150, 400, marker_spacing):
                    if direction == 'in':
                        marker_x = screen_width//2 + math.cos(angle) * dist + offset_x
                        marker_y = screen_height//2 + math.sin(angle) * dist + offset_y
                    else:
                        marker_x = screen_width//2 - math.cos(angle) * (dist-350) + offset_x
                        marker_y = screen_height//2 - math.sin(angle) * (dist-350) + offset_y
                    
                    pygame.draw.rect(screen, (220, 220, 220),
                        (marker_x - math.cos(angle) * marker_length/2,
                         marker_y - math.sin(angle) * marker_length/2,
                         math.cos(angle) * marker_length,
                         math.sin(angle) * marker_length))
    
    # Draw all traffic lights (24 total - 2 per lane per road)
    light_size = 14
    for i in range(1, 7):
        road = f'road{i}'
        angle = math.radians((i-1) * 60)
        
        for direction in ['in', 'out']:
            for lane in [0, 1]:
                lane_offset = 25 if lane == 0 else -25
                dist = 160  # Distance from center
                
                if direction == 'in':
                    light_x = screen_width//2 + math.cos(angle) * dist
                    light_y = screen_height//2 + math.sin(angle) * dist
                else:
                    light_x = screen_width//2 - math.cos(angle) * dist
                    light_y = screen_height//2 - math.sin(angle) * dist
                
                # Adjust for lane position
                light_x += math.cos(angle + math.pi/2) * lane_offset
                light_y += math.sin(angle + math.pi/2) * lane_offset
                
                # Determine light color
                road_key = f"{road}_{direction}"
                if road_key in optimizer.phases[optimizer.current_phase]:
                    color = GREEN if optimizer.current_state == 'green' else (
                        YELLOW if optimizer.current_state == 'yellow' else RED)
                else:
                    color = RED
                
                pygame.draw.circle(screen, BLACK, (int(light_x), int(light_y)), light_size+2)
                pygame.draw.circle(screen, color, (int(light_x), int(light_y)), light_size)

def main():
    roads = [f'road{i}' for i in range(1, 7)]
    optimizer = TrafficLightOptimizer(roads)
    
    # Create initial vehicles
    vehicles = []
    for _ in range(40):  # Fewer initial vehicles for better visibility
        road = random.choice(roads)
        lane = random.randint(0, 1)
        direction = random.choice(['in', 'out'])
        vehicles.append(Vehicle(road, lane, direction))
    
    # Simulation variables
    simulation_time = 0
    running = True
    paused = False
    
    # Main game loop
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_ESCAPE:
                    running = False
        
        if paused:
            # Draw paused text
            pause_text = FONT_LARGE.render("PAUSED - Press SPACE to continue", True, WHITE)
            screen.blit(pause_text, (screen_width//2 - 180, screen_height//2))
            pygame.display.flip()
            clock.tick(30)
            continue
        
        # Clear screen
        screen.fill(BLACK)
        
        # Update simulation time
        simulation_time += 1
        
        # Count vehicles for optimization
        vehicle_counts = defaultdict(int)
        type_counts = defaultdict(lambda: defaultdict(int))
        
        for vehicle in vehicles:
            if vehicle.is_in_intersection() and vehicle.direction == 'in':
                road_key = f"{vehicle.road}_{vehicle.direction}"
                vehicle_counts[road_key] += 1
                type_counts[road_key][vehicle.type] += 1
        
        # Update traffic light state
        status = optimizer.update_phase(vehicle_counts)
        
        # Update vehicles
        for vehicle in vehicles:
            vehicle.update(optimizer)
        
        # Add new vehicles at controlled rate
        if random.random() < 0.02 and len(vehicles) < 60:
            road = random.choice(roads)
            lane = random.randint(0, 1)
            direction = random.choice(['in', 'out'])
            vehicles.append(Vehicle(road, lane, direction))
        
        # Draw everything
        draw_intersection(screen, optimizer)
        
        for vehicle in vehicles:
            vehicle.draw(screen)
        
        # Draw information panel
        panel_width = 300
        pygame.draw.rect(screen, (40, 40, 60), (0, 0, panel_width, screen_height))
        pygame.draw.rect(screen, (80, 80, 100), (0, 0, panel_width, screen_height), 2)
        
        # Display simulation info - TIMINGS AT THE TOP
        y_offset = 20
        
        # Current phase and timing info at the top
        phase_header = FONT_MEDIUM.render(f"PHASE {optimizer.current_phase}", True, WHITE)
        screen.blit(phase_header, (20, y_offset))
        y_offset += 30
        
        # Show optimal times for current phase
        times_header = FONT_MEDIUM.render("GREEN TIMES:", True, WHITE)
        screen.blit(times_header, (20, y_offset))
        y_offset += 30
        
        current_phase_roads = optimizer.phases[optimizer.current_phase]
        for road in current_phase_roads:
            time_val = optimizer.optimal_times.get(road, 0)
            time_text = FONT_SMALL.render(f"{road}: {int(time_val)}s", True, GREEN)
            screen.blit(time_text, (30, y_offset))
            y_offset += 25
        
        y_offset += 20
        
        # Current status
        status_text = FONT_MEDIUM.render(f"STATUS:", True, WHITE)
        screen.blit(status_text, (20, y_offset))
        y_offset += 30
        
        state_color = GREEN if optimizer.current_state == 'green' else (
            YELLOW if optimizer.current_state == 'yellow' else RED)
        state_text = FONT_MEDIUM.render(f"{status}", True, state_color)
        screen.blit(state_text, (30, y_offset))
        y_offset += 40
        
        # Time
        time_text = FONT_MEDIUM.render(f"Time: {simulation_time//10}s", True, WHITE)
        screen.blit(time_text, (20, y_offset))
        y_offset += 40
        
        # Vehicle counts header
        counts_header = FONT_MEDIUM.render("VEHICLE COUNTS:", True, WHITE)
        screen.blit(counts_header, (20, y_offset))
        y_offset += 30
        
        # Vehicle counts per road direction
        for i, road in enumerate(roads):
            for direction in ['in', 'out']:
                road_key = f"{road}_{direction}"
                count = vehicle_counts.get(road_key, 0)
                is_active = road_key in optimizer.phases[optimizer.current_phase]
                road_color = GREEN if is_active and optimizer.current_state == 'green' else WHITE
                
                dir_text = "ENTERING" if direction == 'in' else "EXITING"
                road_text = FONT_SMALL.render(f"{road} {dir_text}: {count}", True, road_color)
                screen.blit(road_text, (30, y_offset))
                y_offset += 25
                
                # Vehicle type breakdown
                for v_type, v_count in type_counts.get(road_key, {}).items():
                    type_text = FONT_SMALL.render(f" - {v_type}: {v_count}", True, VEHICLE_TYPES[v_type]['color'])
                    screen.blit(type_text, (40, y_offset))
                    y_offset += 20
                y_offset += 5
        
        # Controls info
        y_offset = screen_height - 60
        controls_text = FONT_SMALL.render("SPACE: Pause/Resume", True, WHITE)
        screen.blit(controls_text, (20, y_offset))
        y_offset += 25
        quit_text = FONT_SMALL.render("ESC: Quit", True, WHITE)
        screen.blit(quit_text, (20, y_offset))
        
        pygame.display.flip()
        clock.tick(30)
    
    pygame.quit()

if __name__ == "__main__":
    main()