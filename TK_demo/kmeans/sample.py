#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 24 12:54:37 2022

@author: bing
"""

from matplotlib import pyplot as plt


class Sample:
    def __init__(self, attributes:list):
        self.attributes = attributes
        self.data = {}
        
    
    def set_attributes(self, raw_item:str):
        raw_item = raw_item.split(',')
        # print(raw_item)
        for i in range(len(raw_item)):
            try:
                raw_item[i] = float(raw_item[i].strip())
            except ValueError:
                raw_item[i] = raw_item[i].strip()[1:-1]
                
            # if raw_item[i][0].isnumeric():
            #     raw_item[i] = float(raw_item[i].strip())
            # else:
            #     raw_item[i] = raw_item[i].strip()[1:-1]
            
        self.data = {}
        for i in range(len(self.attributes)):
            self.data[self.attributes[i]] = raw_item[i]
        
            
    def get(self, attr:str):
        return self.data[attr]
    
    def set_label(self, label):
        self.label = label
        
    
    def __add__(self, sample):
        new_s = Sample(self.attributes)
        # print(self.data)
        
        for attr in new_s.attributes:
            if type(self.data[attr]) is str:
                new_s.data[attr] = ''
                continue
            new_s.data[attr] = self.data[attr] + sample.data[attr]
        return new_s
            
    
    def __truediv__(self, n):
        
        new_s = Sample(self.attributes)
        for k in self.data.keys():
            if type(self.data[k]) is str:
                continue
            new_s.data[k] = self.data[k]/n
        return new_s
            
        

def plot_samples(samples:list, attr_x, attr_y):
    for s in samples:
        x = s.get(attr_x)
        y = s.get(attr_y)
        if s.get('variety')=="Virginica":
            # c = 'r'
            s = 'v'
        elif s.get('variety')=='Versicolor':
            # c = 'g'
            s = 'o'
        else: ##satosa
            # c = 'b'
            s = 'x'
        c = 'b'
        plt.plot(x, y, s+c)
    plt.show()
        
    

if __name__ == "__main__":
    
    f = open('iris.csv', 'r')
    raw_data = f.readlines()
    # print(raw_data)
    attributes = raw_data[0].split(',')
    
    for i in range(len(attributes)):
        attributes[i] = attributes[i].strip()[1:-1]
        
    samples = []
    
    for item in raw_data[1:]:
        sample = Sample(attributes)
        sample.set_attributes(item)
        samples.append(sample)
        # print(sample.data)
    plot_samples(samples, attributes[1], attributes[3])
        
    


    