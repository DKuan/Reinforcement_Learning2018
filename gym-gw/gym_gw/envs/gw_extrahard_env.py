"""
This file is wrote for the gridworld env, conclude a main module named Grid_World
The class is inherit from the class of Envrionment_Base, and rewrite two methods
"""
#import sys
#sys.path.append('../')
import gym
import numpy as np
from gym import error, spaces, utils
from gym.utils import seeding

VALUE_OWN_POS = 20 
VALUE_FOOD_POS = 100
VALUE_ZERO = 1
grid_depth = 7
grid_width = 14
num_actions = 9

class GridWorldExtraHardEnv(gym.Env):
    metadata = {'render.modes':['human']}

    """
    Rewrite the Env_base and realize the file of grid_world
    """
    def __init__(self):
        """
        for init the env
        arg:
        |num_grid: the num of the grids
        |num_action: the num of the action
        """
        self.action_space = spaces.Discrete(9)
        self.grid_depth = grid_depth
        self.grid_width = grid_width
        self.observation_space = spaces.Box(low=0, high=2, shape=(7, 14), dtype=np.int32) 
        self.num_actions = num_actions # record the num of the actions
        self.cnt_episode_steps = 0
        self.max_episode_steps = 300
        #self.done = False # if the episode is over
        #self.reward = None # return the reward to the agent every step
        self.final_states = []
        self.food_pos = np.array([np.random.randint(1, self.grid_depth), \
            np.random.randint(1, self.grid_width)])
        #self.food_pos = np.array([4, 6]) 
        #self.map = np.ones((self.grid_depth, self.grid_width))
        #self.init_final_state()

    def render(self):
        """ 
        show the grid map
        """
        print(self.map)

    def reset(self):
        """
        reset the env to init state
        """
        """ clear the records for old game """

        """ init the state for new game """
        self.cnt_episode_steps = 0
        self.food_pos = np.array([np.random.randint(1, self.grid_depth), \
            np.random.randint(1, self.grid_width)])
        self.map = np.ones((self.grid_depth, self.grid_width))
        self.place = np.array([np.random.randint(1, self.grid_depth), \
            np.random.randint(1, self.grid_width)])
        self.map[self.food_pos[0]][self.food_pos[1]] = VALUE_FOOD_POS
        self.map[self.place[0]][self.place[1]] = VALUE_OWN_POS

        return self.map

    def range_check(self, num, board_size):
        """
        jthis func for number check
        return the right number 
        arg:
        num: the num should be checked
        board_size: int, show the length of the board
        """
        grid_length = board_size
        if num >= grid_length:
            return grid_length - 1
        elif num < 0 :
            return 0
        else:
            return num

    def step(self, action, in_place=True):
        """
        act the action which the agent do, and return the reward of this action
        arg:
        in_place:true, then change the place number
        action: int, 0-3, up down left right
        """
        done = False
        reward = -1		
        self.cnt_episode_steps += 1
        old_pos = [self.place[0], self.place[1]] # store the old place
        self.map[old_pos[0]][old_pos[1]] = VALUE_ZERO 

        if action == 0: # up left 
            self.place[0] -= 1
            self.place[1] -= 1
        elif action == 1: # up 
            self.place[0] -= 1
        elif action == 2: # up right
            self.place[0] -= 1
            self.place[1] += 1
        elif action == 3: # left
            self.place[1] -= 1
        elif action == 4: # None 
            pass
        elif action == 5: # right
            self.place[1] += 1
        elif action == 6: # down left
            self.place[0] += 1
            self.place[1] -= 1
        elif action == 7: # down 
            self.place[0] += 1
        elif action == 8: # down right
            self.place[0] += 1
            self.place[1] += 1
        else:
            reward = -1 
        """ check the right range of the place """
        self.place[0] = self.range_check(self.place[0], self.grid_depth)	
        self.place[1] = self.range_check(self.place[1], self.grid_width)	

        """ set the reward and done for this episode """
        if tuple(self.place) == tuple(self.food_pos):
            reward = 10
            done = True
        
        if self.cnt_episode_steps > self.max_episode_steps:
            done = True

        self.map[self.place[0]][self.place[1]] = VALUE_OWN_POS 
        place_return = self.place  
        self.place = self.place if in_place == True else old_pos

        return self.map, reward, done, {}

    def close(self):
        pass

if __name__ == "__main__":
        env = Grid_World(7, 14, 4)
        env.reset() 
        env.step(True, 1)
        print(env.map)
        env.step(True, 3)
        print(env.map)