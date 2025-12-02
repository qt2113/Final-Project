#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 19 01:09:26 2022

@author: bing
"""

import os
import sys
sys.path.append(os.getcwd()+'/kmeans')
sys.path.append(os.getcwd()+'/knn')
sys.path.append(os.getcwd()+'/data')

import random
from tkinter import *

from kmeans import kmeans
# from knn import 


class Tools():
    
    def __init__(self, parent):
        self.label =  Label(parent, text="A demo of algorithms in data science.")
        self.label.grid(row=0, columnspan=2)
        
        # self.samples = self.generate_data()
        
        self.k = Entry(parent, width=4)
        self.k.grid(column=1, row=1)
        self.k_label = Label(parent, text="Input the k:")
        self.k_label.grid(column=0, row=1)
        
        self.kmeans_botton = Button(parent, text="Kmeans", command=self.kmeans)
        self.kmeans_botton.grid(columnspan=2, row=3)
        
        self.knn_button = Button(parent, text="knn", fg="red", command=self.knn)
        self.knn_button.grid(columnspan=2, row=4)
    
    def kmeans(self):
        print("kmeans")
        k = int(self.k.get())
        kmeans.run_kmeans_on_iris(k)
        
    def knn(self):
        print("knn")

   
    
    
root = Tk()
root.title("Data Science Tools")
app = Tools(root)
root.mainloop()