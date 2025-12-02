#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 24 12:54:37 2022

@author: bing
"""

from matplotlib import pyplot as plt


def minkowski_distance(x:list, y:list, p:float):
    dist = 0
    for i in range(len(x)):
        dist += abs(x[i]-y[i])**p
    return dist**(1/p)


class Sample:
    def __init__(self, x, y, label=""):
        self.x = x
        self.y =y
        self.label = label
    
    def get_x(self):
        return self.x
    
    def set_x(self, x):
        self.x = x
    
    def get_y(self):
        return self.y
    
    def set_y(self, y):
        self.y = y
    
    def get_label(self):
        return self.label
    
    def set_label(self, label):
        self.label = label
    
    def distance(self, other_sample):
        dist = (self.x-other_sample.get_x())**2 + (self.y-other_sample.get_y())**2
        dist = dist**0.5
        return dist
    
    def __add__(self, other_sample):
        
        x = self.x + other_sample.get_x()
        y = self.y + other_sample.get_y()
        result = Sample(x, y, label="")
        return result
    
    def __truediv__(self, n):
        x = self.x/n
        y = self.y/n
        return Sample(x, y, label="")


def plot_samples(samples:list):
    
    colors = {"Setosa": 'r', "Versicolor": 'g', "Virginica": 'b'}
    shapes = {"Setosa": 'v', "Versicolor": 'o', "Virginica": 'x'}
   
    # plt.figure(1)
    for s in samples:
        if s.get_label()!="":
            color = colors[s.get_label()]
            # print(color)
            shape = shapes[s.get_label()]
        else:
            color = 'b'
            shape = 'o'
        x = s.get_x()
        y = s.get_y()
            
        plt.plot(x, y, shape+color)
            
    plt.show()
            

if __name__ == "__main__":
    
    f = open('iris.csv', 'r')
    raw_data = f.readlines()
   
    raw_data = [item.strip().split(",") for item in raw_data]
    # print(raw_data)
        
    samples = []
    for item in raw_data[1:]: #ignore the first row
        sample = Sample(float(item[0]), float(item[1]), label=item[-1][1:-1])
        samples.append(sample)
        
    plot_samples(samples)
        
    


    