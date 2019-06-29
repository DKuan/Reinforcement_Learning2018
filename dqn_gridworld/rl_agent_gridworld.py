#!/usr/bin/env python3
"""
This is the first generation of the RL agent, based the rule set to make a AI in a general level 
Author: FFAI_WD
Rights Reserved
"""
import os
import sys

""" add the path to the sys.path"""
sys.path.append(os.getcwd())

import gym
import time
import random
import numpy as np
from collections import namedtuple

import torch
import torch.nn as nn
import torch.optim as optim
from model_dqn import DQN
from replay_buffer import PrioritizedReplayBuffer
from schedules import LinearSchedule

action_num = 4
action_list = np.arange(action_num)
Transition = namedtuple('Transition',
        ('state', 'action', 'reward', 'next_state') )

class RL_AGENT_ONE():
    """
    RL agent class
    """
    def __init__(self, memory_size, batch_size, learn_start_time, learn_fre, lr, replay_iters, eps_T, eps_t_init,
        gamma, update_period, board, device, model_path, r_memory_Fname, o_model_name, model_load=False ):
        self.step_now = 0 # record the step
        self.reward_num = 0
        self.reward_accumulated = 0 # delay reward
        self.final_tem = 10 # just for now
        self.step_last_update = 0 # record the last update time 
        self.update_period = update_period # for the off policy
        self.learn_start_time = learn_start_time 
        self.gamma = gamma
        self.batch_size = batch_size
        self.memory_size = memory_size
        self.alpha = 0.6
        self.beta = 0.4
        self.replay_bata_iters = replay_iters 
        self.replay_eps = 1e-6
        self.memory_min_num = 1000 #she min num to learn
        self.step_last_learn = 0 # record the last learn step
        self.learn_fre = learn_fre # step frequency to learn
        self.e_greedy = 1 # record the e_greedy
        self.eps_T = eps_T # par for updating the maybe step 80,0000
        self.eps_t_init = eps_t_init # par for updating the eps
         
        self.device = device
        self.model_path = model_path
        self.mode_enjoy = model_load
        if model_load == False: 
            self.policy_net = DQN(board[0], board[1], action_num).to(device)
            self.target_net = DQN(board[0], board[1], action_num).to(device)
            self.optimizer = optim.Adagrad(self.policy_net.parameters(), lr=lr)
            self.loss_fn = nn.functional.mse_loss # use the l1 loss
            self.memory = PrioritizedReplayBuffer(memory_size, self.alpha)
            self.beta_schedule = LinearSchedule(self.replay_bata_iters, self.beta, 1.0)
        else:
            self.load(o_model_name) 
        #self.optimizer = optim.RMSprop(self.policy_net.parameters(), lr=lr) 
        self.obs_new = None
        self.obs_old = None
        self.action = None
        self.action_old = None
        self.dqn_direct_flag = False # show if the dqn action is done
        self.model_save_flag = False
    
    def reset(self):
        """ 
        reset the flag, state, reward for a new half or game
        """
        self.obs_new = None
        self.obs_old = None
        self.action = None
        self.dqn_direct_flag = False

    def load(self, old_model):
        """
        load the trained model
        par:
        |old_model:str, the name of the old model
        """
        model_path_t = self.model_path + 't' + old_model
        self.target_net = torch.load(model_path_t, map_location=self.device)
        self.target_net.eval()
        print('target net par', self.target_net.state_dict())

    def save(self):
        """
        save the trained model
        """
        #if self.model_path in os.listdir()
        t = time.strftime('%m%d%H%M%S')
        self.model_path_p = self.model_path + 'p' + t + '.pt'
        self.model_path_t = self.model_path + 't' + t + '.pt'
        print('target net par is', self.policy_net.state_dict())
        torch.save(self.policy_net, self.model_path_p)
        torch.save(self.target_net, self.model_path_t)

    def learn(self, env, step_now, obs_old, action, obs_new, reward, done):
        """
        This func is used to learn the agent
        par:
        |step_now: int, the global time of training
        |env: class-Environment, use it for nothing
        |transition: action, obs_new, reward 
        |obs_old/new: instance obs
        |done: bool, if the game is over 
        """
        """ check if we should update the policy net """
        if step_now - self.step_last_update == self.update_period:
            #print('update the p t network')
            self.step_last_update = step_now
            self.target_net.load_state_dict(self.policy_net.state_dict())
                
        """ init the obs_new for init learn """
        state_new = self.feature_combine(obs_new) # get the feature state
        state_old = self.feature_combine(obs_old) # get the feature state
        transition_now = (state_old, action, \
            reward, state_new)

        """ augument reward data to the memory """
        if reward > 0:
            #print('get one reward in learn', self.reward_accumulated)
            self.memory.add(*self.data_augment(transition_now), done)
        self.memory.add(state_old, action, \
            reward, state_new, done)

        """ select the batch memory to update the network """
        step_diff = step_now - self.step_last_learn
        if step_now > self.learn_start_time and \
                step_diff >= self.learn_fre and \
                    self.memory.__len__() > self.memory_min_num:
            self.step_last_learn = step_now # update the self.last learn
            #print('start sample', step_now)
            batch_data = self.memory.sample(self.batch_size, \
                beta=self.beta_schedule.value(step_now))
            loss_list = []
            batch_idx_list = []
            reward_not_zero_cnt = 0
            for t_ in zip(*batch_data):
                s, action, reward, s_new, done, weight, idx = t_
                #print('the transition is', t_)
                """ cnt how many times learn for non reward """
                q_values = self.policy_net(s_new)
                action_new = self.select_egreedy(q_values.cpu().detach().numpy(), self.eps_T*2) 
                #reward = torch.tensor(reward).to(self.device)
                #target_value =reward if done \
                    #else self.gamma*self.target_net(s_new)[action_new] + reward
                target_value = self.gamma*self.target_net(s_new).gather( \
                        0, torch.tensor(action_new, device=self.device))
                target_value = target_value + reward if not done \
                    else  target_value - (target_value - reward)
                loss = self.loss_fn(self.policy_net(s).gather(0, \
                        torch.tensor(action, device=self.device)), target_value)
                loss_list.append(loss + self.replay_eps)
                batch_idx_list.append(idx)

                """ update the par """
                self.optimizer.zero_grad()
                loss.backward()
                #print('self.policy_net linear grad is', self.policy_net.fc_3.bias.grad)
                #print('self.policy_net linear grad is', self.policy_net.fc_3.weight.grad)
                #input()
                for param in self.policy_net.parameters():
                    param.grad.data.clamp_(-1, 1)
                self.optimizer.step()
                #input()
            self.memory.update_priorities(batch_idx_list, loss_list)

        """ check if we should save the model """
        if self.model_save_flag == True:
            self.save()

    def select_egreedy(self, q_value, step_now):
        """
        select the action by e-greedy policy
        arg:
        |q_value: the greedy standard 
        """
        self.e_greedy = np.exp((self.eps_t_init - step_now) / self.eps_T)

        """ if we are in enjoying mode """
        if self.mode_enjoy == True:
            print('q_value is', q_value)
            self.e_greedy = 0

        """ select the action by e-greedy """
        if np.random.random() > self.e_greedy:
            action = action_list[ \
                    np.where(q_value==np.max(q_value))[0][0] ]
        else:
            action = action_list[np.random.randint(action_num)]
        return action

    def feature_combine(self, obs):
        """ 
        This file extract features from the obs.layers and 
        combine them into a new feature layer
        Used feature layers:    
        """
        """ combine all the layers """
        feature_c = obs.copy()
        feature_c = feature_c.astype(np.float32)
        feature_c = torch.tensor(feature_c, dtype=torch.float32, device=self.device)
        size = feature_c.shape
        feature_c = feature_c.resize_(1, 1, size[0], size[1])
        return feature_c

    def data_augment(self, transition):
        """
        use this func to flip the feature, to boost the experience,
        deal the problem of sparse reward
        par:
        |transition: tuple, with (feature_o, action, feature_n, reward) 
        """
        flip_ver_dim = 2
        feature_old = transition[0]
        action = transition[1]
        feature_new = transition[3]
        reward = transition[2]

        """ vertical flip """
        feature_o_aug = feature_old.flip([flip_ver_dim])
        feature_n_aug = feature_new.flip([flip_ver_dim])

        """ vertical :action flip """
        if action == 0:  action = 1
        elif action == 1: action = 0

        return feature_o_aug, action, reward, feature_n_aug

    def act(self, map, step_now):
        """ this func is interact with the competition func """
        dqn_action = -1 # reset
        state_old = self.feature_combine(map) # get the feature
        q_values = self.policy_net(state_old)
        action = self.select_egreedy( \
            q_values.cpu().detach().numpy(), step_now)# features to model

        return action

    def act_enjoy(self, map):
        """ this func is interact with the competition func """
        dqn_action = -1 # reset
        step_now = self.eps_T
        state_old = self.feature_combine(map) # get the feature
        q_values = self.target_net(state_old)
        action = self.select_egreedy( \
            q_values.cpu().detach().numpy(), step_now)# features to model

        return action