from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.actor.Actor import Actor
from direct.interval.IntervalGlobal import Sequence, Parallel, Func, Wait
from panda3d.core import Point3, Vec3, CollisionSphere, CollisionNode
from panda3d.core import AmbientLight, DirectionalLight, PointLight
from panda3d.core import WindowProperties, TextNode, NodePath
from panda3d.core import CollisionTraverser, CollisionHandlerQueue
import random
import sys

class Snake3D(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        
        # Game settings
        self.GRID_SIZE = 20
        self.MOVE_SPEED = 8
        self.INITIAL_SNAKE_LENGTH = 3
        self.FOOD_MODELS = ['models/food1', 'models/food2']  # Example model paths
        
        # Game state
        self.score = 0
        self.game_over = False
        self.paused = False
        self.current_direction = Vec3(1, 0, 0)
        self.next_direction = Vec3(1, 0, 0)
        
        # Initialize game components
        self.setup_scene()
        self.setup_snake()
        self.setup_collisions()
        self.setup_lights()
        self.setup_camera()
        self.setup_ui()
        self.spawn_food()
        
        # Input handling
        self.accept("arrow_left", self.change_direction, [-1, 0, 0])
        self.accept("arrow_right", self.change_direction, [1, 0, 0])
        self.accept("arrow_up", self.change_direction, [0, 1, 0])
        self.accept("arrow_down", self.change_direction, [0, -1, 0])
        self.accept("p", self.toggle_pause)
        self.accept("r", self.restart_game)
        self.accept("escape", sys.exit)
        
        # Start game loop
        self.taskMgr.add(self.game_loop, "GameLoop")

    def setup_scene(self):
        """Setup the game environment and playing field"""
        # Create game board
        self.game_board = self.loader.loadModel("models/board")  # Example model path
        self.game_board.reparentTo(self.render)
        self.game_board.setScale(self.GRID_SIZE, self.GRID_SIZE, 1)
        
        # Setup game boundaries
        self.boundaries = []
        for x in [-self.GRID_SIZE/2, self.GRID_SIZE/2]:
            for y in range(-self.GRID_SIZE//2, self.GRID_SIZE//2):
                self.create_boundary(x, y)
        for y in [-self.GRID_SIZE/2, self.GRID_SIZE/2]:
            for x in range(-self.GRID_SIZE//2, self.GRID_SIZE//2):
                self.create_boundary(x, y)

    def setup_snake(self):
        """Initialize the snake with its starting position and segments"""
        self.snake_segments = []
        self.snake_model = self.loader.loadModel("models/snake_segment")  # Example model path
        
        # Create initial snake segments
        start_pos = Point3(0, 0, 0)
        for i in range(self.INITIAL_SNAKE_LENGTH):
            segment = self.create_snake_segment(start_pos - Point3(i, 0, 0))
            self.snake_segments.append(segment)

    def create_snake_segment(self, position):
        """Create a new snake segment at the given position"""
        segment = self.snake_model.copyTo(self.render)
        segment.setPos(position)
        segment.setScale(0.9)  # Slightly smaller than grid cell
        
        # Add collision detection
        collision_sphere = CollisionSphere(0, 0, 0, 0.5)
        collision_node = segment.attachNewNode(CollisionNode('snakeSegment'))
        collision_node.node().addSolid(collision_sphere)
        
        return segment

    def setup_collisions(self):
        """Setup collision detection system"""
        self.collision_traverser = CollisionTraverser()
        self.collision_queue = CollisionHandlerQueue()
        
        # Setup collision detection for snake head
        self.head_collider = self.snake_segments[0].find("**/snakeSegment")
        self.collision_traverser.addCollider(self.head_collider, self.collision_queue)

    def setup_lights(self):
        """Setup scene lighting"""
        # Ambient light
        ambient_light = AmbientLight("ambient")
        ambient_light.setColor((0.2, 0.2, 0.2, 1))
        self.ambient_light_np = self.render.attachNewNode(ambient_light)
        self.render.setLight(self.ambient_light_np)
        
        # Directional light (sun)
        directional_light = DirectionalLight("directional")
        directional_light.setColor((0.8, 0.8, 0.8, 1))
        directional_light_np = self.render.attachNewNode(directional_light)
        directional_light_np.setHpr(45, -45, 0)
        self.render.setLight(directional_light_np)
        
        # Point light following snake head
        self.snake_light = PointLight("snakeLight")
        self.snake_light.setColor((0.6, 0.6, 1.0, 1))
        self.snake_light_np = self.render.attachNewNode(self.snake_light)
        self.render.setLight(self.snake_light_np)

    def setup_camera(self):
        """Setup and position the game camera"""
        self.camera.setPos(0, -30, 20)
        self.camera.lookAt(Point3(0, 0, 0))
        
        # Set up camera controls
        self.accept("wheel_up", self.adjust_camera_zoom, [-1])
        self.accept("wheel_down", self.adjust_camera_zoom, [1])

    def setup_ui(self):
        """Setup game user interface elements"""
        # Score display
        self.score_text = TextNode('score')
        self.score_text.setText(f"Score: {self.score}")
        self.score_text_np = aspect2d.attachNewNode(self.score_text)
        self.score_text_np.setScale(0.07)
        self.score_text_np.setPos(-1.3, 0, 0.9)
        
        # Game over text (hidden initially)
        self.game_over_text = TextNode('gameOver')
        self.game_over_text.setText("Game Over!\nPress 'R' to restart")
        self.game_over_text_np = aspect2d.attachNewNode(self.game_over_text)
        self.game_over_text_np.setScale(0.15)
        self.game_over_text_np.setPos(-0.5, 0, 0)
        self.game_over_text_np.hide()

    def spawn_food(self):
        """Spawn new food at random position"""
        if hasattr(self, 'food'):
            self.food.removeNode()
        
        # Find valid position (not occupied by snake)
        while True:
            x = random.randint(-self.GRID_SIZE//2 + 1, self.GRID_SIZE//2 - 1)
            y = random.randint(-self.GRID_SIZE//2 + 1, self.GRID_SIZE//2 - 1)
            pos = Point3(x, y, 0)
            
            if not any(segment.getPos().almostEqual(pos, 0.1) 
                      for segment in self.snake_segments):
                break
        
        # Create food
        self.food = self.loader.loadModel(random.choice(self.FOOD_MODELS))
        self.food.reparentTo(self.render)
        self.food.setPos(pos)
        self.food.setScale(0.8)
        
        # Add collision detection
        collision_sphere = CollisionSphere(0, 0, 0, 0.5)
        collision_node = self.food.attachNewNode(CollisionNode('food'))
        collision_node.node().addSolid(collision_sphere)

    def game_loop(self, task):
        """Main game loop"""
        if self.game_over or self.paused:
            return Task.cont
        
        # Update snake position
        dt = globalClock.getDt()
        if self.move_cooldown > 0:
            self.move_cooldown -= dt
        else:
            self.move_snake()
            self.move_cooldown = 1.0 / self.MOVE_SPEED
        
        # Check collisions
        self.check_collisions()
        
        # Update snake light position
        head_pos = self.snake_segments[0].getPos()
        self.snake_light_np.setPos(head_pos + Point3(0, 0, 5))
        
        return Task.cont

    def move_snake(self):
        """Move the snake in the current direction"""
        # Update direction
        self.current_direction = self.next_direction
        
        # Calculate new head position
        old_head_pos = self.snake_segments[0].getPos()
        new_head_pos = old_head_pos + self.current_direction
        
        # Move body segments
        for i in range(len(self.snake_segments) - 1, 0, -1):
            self.snake_segments[i].setPos(self.snake_segments[i-1].getPos())
        
        # Move head
        self.snake_segments[0].setPos(new_head_pos)
        
        # Rotate head to face movement direction
        head_hpr = Vec3(0, 0, 0)
        if self.current_direction.getX() == 1: head_hpr.setZ(90)
        elif self.current_direction.getX() == -1: head_hpr.setZ(-90)
        elif self.current_direction.getY() == 1: head_hpr.setZ(0)
        elif self.current_direction.getY() == -1: head_hpr.setZ(180)
        self.snake_segments[0].setHpr(head_hpr)

    def check_collisions(self):
        """Check for collisions with food, boundaries, and self"""
        self.collision_traverser.traverse(self.render)
        
        for i in range(self.collision_queue.getNumEntries()):
            entry = self.collision_queue.getEntry(i)
            into_node = entry.getIntoNode()
            
            if into_node.getName() == "food":
                self.handle_food_collision()
            elif into_node.getName() == "boundary":
                self.end_game()
            elif into_node.getName() == "snakeSegment" and entry.getFromNode() != into_node:
                self.end_game()

    def handle_food_collision(self):
        """Handle snake eating food"""
        # Increase score
        self.score += 10
        self.score_text.setText(f"Score: {self.score}")
        
        # Add new segment
        last_segment = self.snake_segments[-1]
        new_segment = self.create_snake_segment(last_segment.getPos())
        self.snake_segments.append(new_segment)
        
        # Spawn new food
        self.spawn_food()
        
        # Play eating sound effect
        self.eating_sound.play()

    def change_direction(self, x, y, z):
        """Change snake's direction"""
        new_direction = Vec3(x, y, z)
        # Prevent 180-degree turns
        if not (new_direction + self.current_direction).length() == 0:
            self.next_direction = new_direction

    def end_game(self):
        """Handle game over state"""
        self.game_over = True
        self.game_over_text_np.show()
        
        # Play game over sound
        self.game_over_sound.play()

    def restart_game(self):
        """Restart the game"""
        # Remove existing snake segments
        for segment in self.snake_segments:
            segment.removeNode()
        
        # Reset game state
        self.score = 0
        self.game_over = False
        self.current_direction = Vec3(1, 0, 0)
        self.next_direction = Vec3(1, 0, 0)
        self.move_cooldown = 0
        
        # Reset UI
        self.score_text.setText(f"Score: {self.score}")
        self.game_over_text_np.hide()
        
        # Create new snake
        self.setup_snake()
        self.spawn_food()

    def adjust_camera_zoom(self, direction):
        """Adjust camera zoom level"""
        current_pos = self.camera.getPos()
        new_pos = current_pos + Vec3(0, direction * 2, -direction)
        if -40 <= new_pos.getY() <= -20:  # Limit zoom range
            self.camera.setPos(new_pos)

    def toggle_pause(self):
        """Toggle game pause state"""
        self.paused = not self.paused

# Create and run the game
game = Snake3D()
game.run()
