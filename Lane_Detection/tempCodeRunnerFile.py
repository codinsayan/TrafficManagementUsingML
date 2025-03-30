import pygame
import random
import math
import time
from collections import defaultdict

# Initialize pygame with 1366x768 resolution (common 14" screen size)
pygame.init()
screen_width, screen_height = 1366, 768
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("6-Way Smart Intersection Simulation")
clock = pygame.time.Clock()

# Colors with better contrast
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 50, 50)       # Brighter red
YELLOW = (255, 255, 0)
GREEN = (50, 255, 50)     # Brighter green
GRAY = (120, 120, 120)
ROAD_COLOR = (70, 70, 70) # Lighter road color

# Vehicle types with more distinct colors and sizes
VEHICLE_TYPES = {
    'car': {'width': 28, 'height': 14, 'color': (0, 150, 255), 'speed': (2.5, 4.5)},
    'bus': {'width': 36, 'height': 18, 'color': (255, 120, 0), 'speed': (2, 3.5)},
    'truck': {'width': 40, 'height': 22, 'color': (180, 80, 0), 'speed': (1.5, 3)},
    'motorcycle': {'width': 22, 'height': 10, 'color': (255, 255, 100), 'speed': (3.5, 6)}
}

# Font settings for better readability
FONT_LARGE = pygame.font.SysFont('Arial', 24, bold=True)
FONT_MEDIUM = pygame.font.SysFont('Arial', 20)
FONT_SMALL = pygame.font.SysFont('Arial', 16)

class TrafficLightOptimizer:
    def __init__(self, roads):
        self.roads = roads
        self.min_green_time = 12  # Increased minimum time
        self.max_green_time = 50
        self.yellow_time = 4      # Longer yellow for visibility
        self.current_phase = 0
        self.phases = self.generate_phases()
        self.current_state = 'red'
        self.state_start_time = time.time()
        self.weights = {road: 1.0 for road in roads}
        self.weights['road1'] = 1.3  # Main roads get higher priority
        self.weights['road4'] = 1.2
        
    def generate_phases(self):
        return [
            ['road1', 'road4'],  # Phase 0
            ['road2', 'road5'],   # Phase 1
            ['road3', 'road6']    # Phase 2
        ]
    
    def calculate_optimal_times(self, vehicle_counts):
        total_weighted_vehicles = sum(count * self.weights.get(road, 1.0) 
                                  for road, count in vehicle_counts.items())
        
        if total_weighted_vehicles < 2:  # Minimum vehicles threshold
            return {road: self.min_green_time for road in self.roads}
        
        green_times = {}
        current_phase_roads = self.phases[self.current_phase]
        
        for road in current_phase_roads:
            proportion = (vehicle_counts[road] * self.weights.get(road, 1.0)) / total_weighted_vehicles
            green_time = self.min_green_time + proportion * (self.max_green_time - self.min_green_time)
            green_times[road] = min(self.max_green_time, max(self.min_green_time, round(green_time)))
        
        return green_times
    
    def update_phase(self, vehicle_counts):
        current_time = time.time()
        state_duration = current_time - self.state_start_time
        
        if self.current_state == 'green':
            optimal_times = self.calculate_optimal_times(vehicle_counts)
            avg_green_time = sum(optimal_times.values()) / len(optimal_times)
            
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
            if state_duration >= 1.5:  # Slightly longer all-red
                self.current_state = 'green'
                self.state_start_time = current_time
                return f"PHASE {self.current_phase} GREEN"
        
        return f"PHASE {self.current_phase} {self.current_state.upper()}"

class Vehicle:
    def __init__(self, road, lane, direction):
        self.road = road
        self.lane = lane  # 0 or 1
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
        angle = (int(self.road[-1]) - 1) * 60  # 60° between roads
        distance = 450 if self.direction == 'in' else 180
        lane_offset = 30 if self.lane == 0 else -30
        
        # Calculate position based on angle and lane
        x = screen_width//2 + math.cos(math.radians(angle)) * distance
        y = screen_height//2 + math.sin(math.radians(angle)) * distance
        # Adjust for lane
        x += math.cos(math.radians(angle + 90)) * lane_offset
        y += math.sin(math.radians(angle + 90)) * lane_offset
        
        return x, y
    
    def update(self, optimizer):
        in_intersection = self.is_in_intersection()
        should_stop = False
        
        # Check if vehicle needs to stop
        if in_intersection and not self.passed_intersection:
            active_roads = optimizer.phases[optimizer.current_phase]
            if optimizer.current_state != 'green' or self.road not in active_roads:
                should_stop = True
                self.waiting_time += 1
            else:
                self.passed_intersection = True
        
        if not should_stop:
            # Move vehicle based on direction
            angle = (int(self.road[-1]) - 1) * 60
            move_x = math.cos(math.radians(angle)) * self.speed
            move_y = math.sin(math.radians(angle)) * self.speed
            
            if self.direction == 'in':
                self.x -= move_x
                self.y -= move_y
            else:
                self.x += move_x
                self.y += move_y
        
        # Reset if vehicle goes off screen
        if self.is_off_screen():
            self.__init__(self.road, self.lane, self.direction)
    
    def is_in_intersection(self):
        distance = math.sqrt((self.x - screen_width//2)**2 + (self.y - screen_height//2)**2)
        return distance < 150
    
    def is_off_screen(self):
        return (self.x < -150 or self.x > screen_width + 150 or 
                self.y < -150 or self.y > screen_height + 150)
    
    def draw(self, screen):
        angle = (int(self.road[-1]) - 1) * 60
        if self.direction == 'out':
            angle += 180
        
        # Draw vehicle with better visibility
        vehicle_surface = pygame.Surface((self.width+4, self.height+4), pygame.SRCALPHA)
        pygame.draw.rect(vehicle_surface, self.color, (2, 2, self.width, self.height))
        pygame.draw.rect(vehicle_surface, BLACK, (2, 2, self.width, self.height), 1)  # Border
        rotated_vehicle = pygame.transform.rotate(vehicle_surface, -angle)
        rect = rotated_vehicle.get_rect(center=(self.x, self.y))
        screen.blit(rotated_vehicle, rect.topleft)

def draw_intersection(screen, optimizer):
    # Draw the circular intersection center with better visibility
    pygame.draw.circle(screen, ROAD_COLOR, (screen_width//2, screen_height//2), 150)
    pygame.draw.circle(screen, (100, 100, 100), (screen_width//2, screen_height//2), 150, 3)  # Border
    
    # Draw 6 roads at 60 degree intervals with better lane markings
    for i in range(1, 7):
        angle = math.radians((i-1) * 60)
        start_x = screen_width//2 + math.cos(angle) * 150
        start_y = screen_height//2 + math.sin(angle) * 150
        end_x = screen_width//2 + math.cos(angle) * 500
        end_y = screen_height//2 + math.sin(angle) * 500
        
        # Draw road (two lanes)
        road_width = 60  # Wider roads
        pygame.draw.line(screen, ROAD_COLOR, (start_x, start_y), (end_x, end_y), road_width)
        
        # Draw lane markers (more visible)
        for lane in [-1, 1]:
            offset_x = math.cos(angle + math.pi/2) * 20 * lane
            offset_y = math.sin(angle + math.pi/2) * 20 * lane
            for segment in range(0, 400, 40):  # Longer dashes
                seg_x = start_x + math.cos(angle) * segment
                seg_y = start_y + math.sin(angle) * segment
                pygame.draw.rect(screen, (220, 220, 220), 
                    (seg_x + offset_x - 8, seg_y + offset_y - 8, 16, 16))
    
    # Draw all 12 traffic lights with better visibility
    light_size = 16  # Larger lights
    for i in range(1, 7):
        road = f'road{i}'
        angle = math.radians((i-1) * 60)
        
        for lane in [0, 1]:
            lane_offset = 25 if lane == 0 else -25
            offset_x = math.cos(angle + math.pi/2) * lane_offset
            offset_y = math.sin(angle + math.pi/2) * lane_offset
            
            light_x = screen_width//2 + math.cos(angle) * 160 + offset_x
            light_y = screen_height//2 + math.sin(angle) * 160 + offset_y
            
            # Determine light color with black border for contrast
            if road in optimizer.phases[optimizer.current_phase]:
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
    for _ in range(50):  # Fewer initial vehicles for better visibility
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
                    paused = not paused  # Space to pause
        
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
            distance = math.sqrt((vehicle.x - screen_width//2)**2 + (vehicle.y - screen_height//2)**2)
            if distance < 200 and vehicle.direction == 'in':
                vehicle_counts[vehicle.road] += 1
                type_counts[vehicle.road][vehicle.type] += 1
        
        # Update traffic light state
        status = optimizer.update_phase(vehicle_counts)
        optimal_times = optimizer.calculate_optimal_times(vehicle_counts)
        
        # Update vehicles
        for vehicle in vehicles:
            vehicle.update(optimizer)
        
        # Add new vehicles at controlled rate
        if random.random() < 0.02 and len(vehicles) < 70:  # Fewer vehicles
            road = random.choice(roads)
            lane = random.randint(0, 1)
            direction = random.choice(['in', 'out'])
            vehicles.append(Vehicle(road, lane, direction))
        
        # Draw everything
        draw_intersection(screen, optimizer)
        
        for vehicle in vehicles:
            vehicle.draw(screen)
        
        # Draw information panel with better layout
        panel_width = 300
        pygame.draw.rect(screen, (40, 40, 60), (0, 0, panel_width, screen_height))
        pygame.draw.rect(screen, (80, 80, 100), (0, 0, panel_width, screen_height), 2)
        
        # Display simulation info
        y_offset = 20
        title = FONT_LARGE.render("TRAFFIC CONTROL", True, WHITE)
        screen.blit(title, (panel_width//2 - title.get_width()//2, y_offset))
        y_offset += 40
        
        # Current status
        status_text = FONT_MEDIUM.render(f"STATUS:", True, WHITE)
        screen.blit(status_text, (20, y_offset))
        y_offset += 30
        
        state_color = GREEN if optimizer.current_state == 'green' else (
            YELLOW if optimizer.current_state == 'yellow' else RED)
        state_text = FONT_MEDIUM.render(f"{status}", True, state_color)
        screen.blit(state_text, (30, y_offset))
        y_offset += 40
        
        # Time and phase
        time_text = FONT_MEDIUM.render(f"Time: {simulation_time//10}s", True, WHITE)
        screen.blit(time_text, (20, y_offset))
        y_offset += 30
        
        phase_text = FONT_MEDIUM.render(f"Phase: {optimizer.current_phase}", True, WHITE)
        screen.blit(phase_text, (20, y_offset))
        y_offset += 40
        
        # Vehicle counts header
        counts_header = FONT_MEDIUM.render("VEHICLE COUNTS:", True, WHITE)
        screen.blit(counts_header, (20, y_offset))
        y_offset += 30
        
        # Vehicle counts per road
        for i, road in enumerate(roads):
            count = vehicle_counts[road]
            is_active = road in optimizer.phases[optimizer.current_phase]
            road_color = GREEN if is_active and optimizer.current_state == 'green' else WHITE
            
            road_text = FONT_SMALL.render(f"{road}: {count}", True, road_color)
            screen.blit(road_text, (30, y_offset))
            y_offset += 25
            
            # Vehicle type breakdown
            for v_type, v_count in type_counts[road].items():
                type_text = FONT_SMALL.render(f" - {v_type}: {v_count}", True, VEHICLE_TYPES[v_type]['color'])
                screen.blit(type_text, (40, y_offset))
                y_offset += 20
            y_offset += 5
        
        # Optimal times header
        times_header = FONT_MEDIUM.render("OPTIMAL TIMES:", True, WHITE)
        screen.blit(times_header, (20, y_offset))
        y_offset += 30
        
        # Display optimal times
        for road in roads:
            time_val = optimal_times.get(road, 0)
            is_active = road in optimizer.phases[optimizer.current_phase]
            time_color = GREEN if is_active else WHITE
            
            time_text = FONT_SMALL.render(f"{road}: {int(time_val)}s", True, time_color)
            screen.blit(time_text, (30, y_offset))
            y_offset += 25
        
        # Controls info
        y_offset = screen_height - 60
        controls_text = FONT_SMALL.render("SPACE: Pause/Resume", True, WHITE)
        screen.blit(controls_text, (20, y_offset))
        y_offset += 25
        quit_text = FONT_SMALL.render("ESC: Quit", True, WHITE)
        screen.blit(quit_text, (20, y_offset))
        
        pygame.display.flip()
        clock.tick(30)  # Consistent 30 FPS
    
    pygame.quit()

if __name__ == "__main__":
    main()