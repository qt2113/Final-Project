#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Apr 17 17:06:47 2022

@author: bing
"""

from tkinter import *

# import tkinter as tk

class HelloWorld:
    
    def __init__(self, parent): 
        self.label = Label(parent, text="Hello World!")
        self.label.grid(column=0, row=0)
        self.hello_button = Button(parent, text="Say hi", command=self.say_hi)
        self.hello_button.grid(column=0, row=1)
        self.quit_button = Button(parent, text="Quit", fg="red", command=parent.destroy)
        self.quit_button.grid(column=1, row=1)
        
    def say_hi(self):
        print("Hi there")
        

root = Tk()
app = HelloWorld(root)
root.mainloop()
        
    