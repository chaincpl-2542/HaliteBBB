#!/usr/bin/env python3
# Python 3.6

import math
import random
import logging
from enum import Enum

# Import the Halite SDK
import hlt
from hlt import constants
from hlt.positionals import Direction, Position

""" <<<Game Begin>>> """
game = hlt.Game()
game.ready("Normal")

logging.info(f"Successfully created bot! My Player ID is {game.my_id}.")

class BotState(Enum):
    SEARCH = 1
    MOVE_TO_TARGET = 2
    COLLECTING = 3
    BACK_TO_HOME = 4

""" <<<Game Loop>>> """
ship_stage = {}

# Utility Functions
def get_neighbors(position):
    """Returns valid neighboring positions."""
    directions = [Direction.North, Direction.South, Direction.East, Direction.West]
    neighbors = []
    for direction in directions:
        neighbors.append(position.directional_offset(direction))
    return neighbors

def heuristic(pos1, pos2):
    """Manhattan distance heuristic."""
    return abs(pos1.x - pos1.y) + abs(pos2.x - pos2.y)

def calculate_team_halite(game):
    """Calculate the total halite for each team."""
    team_halite = {}

    # Add halite carried by ships and dropoffs/shipyards
    for player_id, player in game.players.items():
        total_halite = player.halite_amount  # Halite stored by the player
        # Add halite carried by ships
        for ship in player.get_ships():
            total_halite += ship.halite_amount
        # Add halite in the map (for all players, not just the player's cells)
        team_halite[player_id] = total_halite

    return team_halite
def a_star(game_map, source, target):
    """A* pathfinding to navigate from source to target."""
    open_set = [source]
    closed_set = set()
    came_from = {}

    gScore = {source: 0}
    fScore = {source: heuristic(source, target)}

    while open_set:
        current = min(open_set, key=lambda pos: fScore.get(pos, float('inf')))

        if current == target:
            # Reconstruct path
            path = []
            while current in came_from:
                path.insert(0, current)
                current = came_from[current]
            return path  # Return the path to follow

        open_set.remove(current)
        closed_set.add(current)

        for neighbor in get_neighbors(current):
            if neighbor in closed_set or game_map[neighbor].is_occupied:
                continue

            tentative_gScore = gScore[current] + game_map[neighbor].halite_amount / 10  # Example cost

            if neighbor not in open_set:
                open_set.append(neighbor)

            if tentative_gScore >= gScore.get(neighbor, float('inf')):
                continue

            came_from[neighbor] = current
            gScore[neighbor] = tentative_gScore
            fScore[neighbor] = gScore[neighbor] + heuristic(neighbor, target)

    return []  # No path found

while True:
    game.update_frame()
    me = game.me
    game_map = game.game_map

    team_halite = calculate_team_halite(game)
    for player_id, total in team_halite.items():
        logging.info(f"Player {player_id} Total Halite: {total}")

    command_queue = []

    for ship in me.get_ships():
        if ship.id not in ship_stage:
            ship_stage[ship.id] = BotState.MOVE_TO_TARGET

        if ship_stage[ship.id] == BotState.MOVE_TO_TARGET:
            # Look for the best halite nearby
            halite_values = {}
            direction_values = {}
            for direction in [Direction.North, Direction.South, Direction.East, Direction.West]:
                pos = ship.position.directional_offset(direction)
                if not game_map[pos].is_occupied:
                    halite_values[pos] = game_map[pos].halite_amount
                    direction_values[pos] = direction

            # Move towards the place with the highest halite
            if halite_values:
                highest_halite_pos = max(halite_values, key=halite_values.get)
                direction = direction_values[highest_halite_pos]
                game_map[ship.position.directional_offset(direction)].mark_unsafe(ship)
                command_queue.append(ship.move(direction))
            else:
                command_queue.append(ship.stay_still())

            ship_stage[ship.id] = BotState.COLLECTING

        elif ship_stage[ship.id] == BotState.COLLECTING:
            command_queue.append(ship.stay_still())
            if ship.halite_amount >= constants.MAX_HALITE or game_map[ship.position].halite_amount < 20:
                ship_stage[ship.id] = BotState.BACK_TO_HOME if ship.halite_amount >= constants.MAX_HALITE else BotState.MOVE_TO_TARGET

        elif ship_stage[ship.id] == BotState.BACK_TO_HOME:
            # Use A* to navigate back to the shipyard
            path = a_star(game_map, ship.position, me.shipyard.position)
            if path:
                next_position = path[0]
                direction = game_map.get_unsafe_moves(ship.position, next_position)[0]
                game_map[ship.position.directional_offset(direction)].mark_unsafe(ship)
                command_queue.append(ship.move(direction))
            else:
                command_queue.append(ship.stay_still())

            if ship.position == me.shipyard.position:
                ship_stage[ship.id] = BotState.MOVE_TO_TARGET

    # Spawn ships if appropriate
    if game.turn_number <= constants.MAX_TURNS - 50 and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    game.end_turn(command_queue)
