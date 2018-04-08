import pygame
import logging
import sys
import random

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


SCREEN_SIZE = (600, 600)


class Controller():

    PRESTART = 1
    RUNNING = 2
    GAMEOVER = 3

    def __init__(self):
        self.events = {}
        self.keymap = {}

        pygame.init()
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        pygame.display.set_caption('Space Dodger')
        self.clock = pygame.time.Clock()

        self.register_eventhandler(pygame.QUIT, self.quit)
        self.register_key(pygame.K_ESCAPE, self.quit)

        self.world = World(self)
        self.rocket = Rocket(self)
        self.stones = [Stone(self)]
        self.diamonds = Diamonds(self)

        self.game_state = Controller.PRESTART

        self.score = 0
        self.points_for_diamonds = 1000
        self.level = 1
        self.diamond_count = 0

        self.stone_count = 0

    def run(self):
        while True:
            # -- Handle all events -------------------------------------------
            for event in pygame.event.get():
                logger.debug('Handling event {}'.format(event))

                # Handle events
                for event_type, callbacks in self.events.items():
                    if event.type == event_type:
                        for callback in callbacks:
                            callback(event)

                # Handle keypresses
                if event.type == pygame.KEYDOWN:
                    for key in self.keymap.keys():
                        if event.key == key:
                            for callback in self.keymap[key]:
                                callback(event)
                        if event.key == pygame.K_r:
                            self.game_state = Controller.PRESTART

            # -- Give everyone a chance to update their state ----------------
            self.rocket.update()
            for stone in self.stones:
                stone.update()

            # -- Fire new stone ----------------------------------------------

            for stone in self.stones:
                if stone.y > SCREEN_SIZE[1] + stone.radius:
                    logger.debug('Stone number: {}'.format(self.stone_count + 1))
                    self.stone_count += 1
                    if self.stone_count == self.level:
                        logger.debug('Level up!'.format(self.stone_count))
                        stone.respawn()
                        for stone in range(self.level):
                            self.stones.append(Stone(self))
                        self.stone_count = 0
                        self.level += 1
                    else:
                        stone.remover()

            # -- Gameover check ----------------------------------------------
            for stone in self.stones:
                pyth_x = abs(self.rocket.x - stone.x)
                pyth_y = abs(self.rocket.y - stone.y)

                if (((pyth_x - self.rocket.half_side + 2) ** 2) +
                   ((pyth_y - self.rocket.half_side + 2) ** 2) <
                   stone.radius ** 2):
                    self.game_state = Controller.GAMEOVER

            # -- Diamonds! --------------------------------------------------
            # x2 for easier capture
            if (abs(self.rocket.x - self.diamonds.x) < 2 * self.diamonds.size and
                abs(self.rocket.y - self.diamonds.y) < 2 * self.diamonds.size):
                self.diamond_count += 1
                self.diamonds.restart()

            # -- Scoreboard -------------------------------------------------
            self.score = self.points_for_diamonds * self.diamond_count
            self.score = self.score * self.level

            # -- Continue of Scoreboard, Text -------------------------------
            white = (238, 238, 238)
            score_message = 'Level {}   Current score = {}'.format(self.level, self.score)
            gameover_message = 'Gameover!'
            restart_message = 'Press r to restart'
            font_main = pygame.font.Font('Fonts/SpaceMono.ttf', 25)
            font_gameover = pygame.font.Font('Fonts/SpaceMono.ttf', 50)
            text_score = font_main.render(score_message, 1, white)
            text_gameover = font_gameover.render(gameover_message, 1, white)
            text_restart = font_main.render(restart_message, 1, white)

            # -- Restart / Start game ----------------------------------------
            if self.game_state == Controller.PRESTART:
                logger.debug('restarting...')
                self.stones = [Stone(self)]

                self.rocket.restart()
                for stone in self.stones:
                    stone.restart()
                self.diamonds.restart()
                self.level = 1
                self.score = 0
                self.diamond_count = 0

                self.game_state = Controller.RUNNING

            # -- Draw everything on screen -----------------------------------
            if self.game_state == Controller.RUNNING:
                self.world.draw()
                self.rocket.draw()
                for stone in self.stones:
                    stone.draw()
                self.diamonds.draw()
                self.screen.blit(text_score, (5, 5))

            # -- Gameover text -----------------------------------------------
            if self.game_state == Controller.GAMEOVER:
                self.screen.blit(text_gameover, (SCREEN_SIZE[0] / 2 - 125, SCREEN_SIZE[1] / 2 - 25))
                self.screen.blit(text_restart, (SCREEN_SIZE[0] / 2 - 125, SCREEN_SIZE[1] - 50))

            # -- Display -----------------------------------------------------
            pygame.display.flip()

            # -- Updates per second ------------------------------------------
            self.clock.tick(60)

    # -- Quit game function --------------------------------------------------
    def quit(self, event):
        logger.info('Quitting... Good bye!')
        pygame.quit()
        sys.exit()

    # -- Register event-type -------------------------------------------------
    def register_eventhandler(self, event_type, callback):
        logger.debug('Registering event handler ({}, {})'.format(event_type, callback))
        if self.events.get(event_type):
            self.events[event_type].append(callback)
        else:
            self.events[event_type] = [callback]

    # -- Register key --------------------------------------------------------
    def register_key(self, key, callback):
        logger.debug('Binding key {} to {}.'.format(key, callback))
        if self.keymap.get(key):
            self.keymap[key].append(callback)
        else:
            self.keymap[key] = [callback]


# -- Player-controlled unit --------------------------------------------------
class Rocket():
    def __init__(self, controller):
        self.controller = controller
        self.screen = controller.screen

        self.controller.register_eventhandler(pygame.KEYDOWN, self.keydown)
        self.controller.register_eventhandler(pygame.KEYUP, self.keyup)

        self.color = {'rocket': pygame.Color('#166BCC'),
                        'boost': pygame.Color('#CC4700')}

        self.correction = 3

        self.half_side = 10
        self.full_side = 2 * self.half_side
        self.placements = 2 + self.half_side / 2

        self.restart()

    # -- Draw the rocket -----------------------------------------------------
    def draw(self):
        surface = pygame.Surface((self.full_side + 4, self.full_side + 4),
                                flags=pygame.SRCALPHA)
        surface.fill(self.color['rocket'], (2, 2, self.full_side, self.full_side))

        if self.main_booster == "boost_up":
            surface.fill(self.color['boost'], (self.placements, self.full_side + 2, self.half_side, 2))
        if self.main_booster == "boost_down":
            surface.fill(self.color['boost'], (self.placements, 0, self.half_side, 2))
        if self.side_booster == "boost_right":
            surface.fill(self.color['boost'], (0, self.placements, 2, self.half_side))
        if self.side_booster == "boost_left":
            surface.fill(self.color['boost'], (self.full_side + 2, self.placements, 2, self.half_side))

        self.screen.blit(surface, (self.x - self.half_side, self.y - self.half_side))

    # -- Rocket-movement -----------------------------------------------------
    def update(self):
        # Calculate new speed and direction
        if self.main_booster == "boost_up":
            self.y_speed -= self.acceleration
        elif self.main_booster == "boost_down":
            self.y_speed += self.acceleration
        else:
            self.y_speed = self.y_speed / self.deceleration

        if self.side_booster == "boost_right":
            self.x_speed += self.acceleration
        elif self.side_booster == "boost_left":
            self.x_speed -= self.acceleration
        else:
            self.x_speed = self.x_speed / self.deceleration

        # Building walls
        if self.x < self.half_side + self.correction:
            self.x = self.half_side + self.correction
            self.x_speed = 0

        elif self.x > SCREEN_SIZE[0] - self.half_side - 2 * self.correction:
            self.x = SCREEN_SIZE[0] - self.half_side - 2 * self.correction
            self.x_speed = 0

        if self.y < self.half_side + self.correction:
            self.y = self.half_side + self.correction
            self.y_speed = 0

        elif self.y > SCREEN_SIZE[1] - self.half_side - 2 * self.correction:
            self.y = SCREEN_SIZE[1] - self.half_side - 2 * self.correction
            self.y_speed = 0

        # Calculate new position
        self.y = self.y + self.y_speed
        self.x = self.x + self.x_speed

    # -- Setting the rocket back to startstate -------------------------------
    def restart(self):
        self.x = SCREEN_SIZE[0] / 2
        self.y = SCREEN_SIZE[1] / 4 * 3
        self.x_speed = 0
        self.y_speed = 0
        self.acceleration = 0.3
        self.deceleration = 1.1
        self.main_booster = False
        self.side_booster = False

    # -- Keys for controlling the rocket -------------------------------------
    def keydown(self, event):
        if event.key == pygame.K_UP or event.key == pygame.K_w:
            self.main_booster = "boost_up"
        elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
            self.main_booster = "boost_down"
        if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
            self.side_booster = "boost_right"
        elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
            self.side_booster = "boost_left"

    # -- Keys for controlling the rocket -------------------------------------
    def keyup(self, event):
        if event.key == pygame.K_UP or event.key == pygame.K_w:
            self.main_booster = False
        elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
            self.main_booster = False
        if event.key == pygame.K_RIGHT or event.key == pygame.K_d:
            self.side_booster = False
        elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
            self.side_booster = False


# -- Untouchable object (gameover if touched) --------------------------------
class Stone():
    def __init__(self, controller):
        self.controller = controller
        self.screen = controller.screen

        self.color = pygame.Color('#961C12')

        self.radius = 20
        self.mid_of_circle = (self.radius, self.radius)
        self.diameter = self.radius * 2

        self.restart()

        self.x = random.randint(self.radius, SCREEN_SIZE[0] - self.radius)
        self.y = -self.radius * 5
        self.y_speed = random.randint(self.low_roll, self.high_roll) / 100

    # -- Draw stone function -------------------------------------------------
    def draw(self):
        surface = pygame.Surface((self.diameter, self.diameter),
                                    flags = (pygame.SRCALPHA))
        pygame.draw.circle(surface, self.color, (self.mid_of_circle), self.radius)
        self.screen.blit(surface, (self.x - self.radius, self.y - self.radius))

    # -- Stone movement ------------------------------------------------------
    def update(self):
        self.y = self.y + self.y_speed

    # -- Respawning stone after level up -------------------------------------
    def respawn(self):
        self.x = random.randint(self.radius, SCREEN_SIZE[0] - self.radius)
        self.y = -self.radius * 2

        self.low_roll += self.low_roll_change
        self.high_roll += self.high_roll_change
        self.y_speed = random.randint(self.low_roll, self.high_roll) / 100

    # -- Setting stone to startstate -----------------------------------------
    def restart(self):
        self.x = random.randint(self.radius, SCREEN_SIZE[0] - self.radius)
        self.y = -self.radius * 2

        self.low_roll = 100
        self.high_roll = 300
        self.low_roll_change = 25
        self.high_roll_change = 75

    # -- Temporary putting a stone out of play -------------------------------
    def remover(self):
        self.x = 2 * -self.radius
        self.y = 2 * -self.radius
        self.y_speed = 0


# -- Score-generating unit ------------------------------------------------------------
class Diamonds():
    def __init__(self, controller):
        self.controller = controller
        self.screen = controller.screen

        self.color = pygame.Color('#A2FF1E')

        self.size = 10

        self.restart()

    # -- Draw diamond function -----------------------------------------------
    def draw(self):
        surface = pygame.Surface((self.size, self.size),
                                flags=pygame.SRCALPHA)
        surface.fill(self.color, (0, 0, self.size, self.size))
        surface = pygame.transform.rotate(surface, 45)

        self.screen.blit(surface, (self.x - self.size / 2, self.y - self.size / 2))

    # -- Give diamond new position -------------------------------------------
    def restart(self):
        self.x = random.randint(15, SCREEN_SIZE[0] - 15)
        self.y = random.randint(100, SCREEN_SIZE[1] - 15)


# -- Background --------------------------------------------------------------
class World():
    def __init__(self, controller):
        self.controller = controller
        self.screen = controller.screen

    # -- Draw world function -------------------------------------------------
    def draw(self):
        surface = pygame.Surface(SCREEN_SIZE)
        surface.fill(pygame.Color('#EEEEEE'), (0, 0, SCREEN_SIZE[0], SCREEN_SIZE[1]))
        surface.fill(pygame.Color('#111111'), (5, 5, SCREEN_SIZE[0] - 10, SCREEN_SIZE[1] - 10))

        self.screen.blit(surface, (0, 0))


# -- Start game from console when called--------------------------------------
if __name__ == "__main__":
    c = Controller()
    c.run()
