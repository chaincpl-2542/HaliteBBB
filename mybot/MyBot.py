#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt
from enum import Enum
import math

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction, Position

# This library allows you to generate random numbers.
import random

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
game.ready("BBB (BigBrainBot)")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """
class BotState(Enum):
    SEARCH = 1
    MOVE_TO_TARGET = 2
    COLLECTING = 3
    BACK_TO_HOME = 4
    
target = None
home = Position(0,0)
state = BotState.SEARCH
distance = 1

while True:
    game.update_frame()
    me = game.me
    game_map = game.game_map

    command_queue = []
    surrounding_vectors = []
    
    for ship in me.get_ships():
        if state == BotState.SEARCH:
            halite_value = []
            for x_offset in range(-distance, distance + 1):
                for y_offset in range(-distance, distance + 1):
                    if abs(x_offset) + abs(y_offset) == distance or (abs(x_offset) == distance and abs(y_offset) == distance):
                        surrounding_vectors.append((ship.position.x + x_offset, ship.position.y + y_offset))
                        
            print(len(surrounding_vectors))
            for vector in surrounding_vectors:
                
                halite_value[vector] = game_map[vector].halite_amount
                print(vector + " : " + halite_value[vector])
            
            if target != None:
                state = BotState.MOVE_TO_TARGET
                
        elif state == BotState.MOVE_TO_TARGET:
            
            if game_map[ship.position].halite_amount < constants.MAX_HALITE / 10 or ship.is_full:
                    
                d = Position(0,0)
                d.x = target.x - ship.position.x
                d.y = target.y - ship.position.y
                
                cmd = Direction.Still
                
                if d.x > 0:
                    cmd = Direction.East
                if  d.x < 0:
                    cmd = Direction.West
                if d.y > 0:
                    cmd = Direction.South
                if  d.y < 0:
                    cmd = Direction.North
                    
                command_queue.append(ship.move(cmd))
                
            else:
                
                if target == None:
                    state = BotState.SEARCH

    if game.turn_number <= 200 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    game.end_turn(command_queue)

