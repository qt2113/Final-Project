#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 24 12:54:54 2022

@author: bing
"""



class Cluster:
    
    def __init__(self, label:int, attributes):
        
        self.label = label
        self.attributes = attributes
        self.samples = []
        
        
    def add_sample(self, sample):
        self.samples.append(sample)
        
        
    def get_center(self):
        
        if self.samples:
            center = self.samples[0]
            for s in self.samples[1:]:
                center += s
            
            center = center/len(self.samples)
            # center.attributes = self.attributes
            # for k in center.data.keys():
            #     if k in center.attributes:
            #         continue
            #     else:
            #         del center.data[k]

            return center
        
        return None
    
    
    
    
        
        