#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jul 24 12:55:34 2022

@author: bing
"""


from sample import Sample, plot_samples
from cluster import Cluster
from sklearn.cluster import KMeans
from matplotlib import pyplot as plt


def run_kmeans(samples, attributes, k=2):
    data = []
    for s in samples:
        attrs = []
        for attr in attributes:
            attrs.append(s.get(attr))
        data.append(attrs)
        
    kmeans = KMeans(k).fit(data)
    # print("kmeans", help(kmeans.fit))
    labels = kmeans.labels_
    
    clusters = []
    for i in range(k):
        cluster = Cluster(i, attributes)
        for j in range(len(labels)):
            if labels[j]==i:
                samples[j].set_label(j)
                cluster.add_sample(samples[j])
        clusters.append(cluster)
    
    return clusters


def plot_clusters(clusters):
    colors = ['r', 'g', 'b', 'c', 'm', 'k']
    shapes = ['v', 'o', 'x', 'd', '+', 's',]
    # plt.figure(1)
    for idx, c in enumerate(clusters):
        color = colors[idx]
        for s in c.samples:
            x = s.get(c.attributes[0])
            y = s.get(c.attributes[1])
            if s.get('variety')=="Virginica":
                shape = shapes[0]
            elif s.get('variety')=='Versicolor':
                shape = shapes[1]
            else: #setosa
                shape = shapes[2]
            # plt.plot(x, y, shape+color)
            plt.plot(x, y, 'o'+color)
        center = c.get_center()
        plt.plot(center.get(c.attributes[0]), center.get(c.attributes[1]), 'ks')
    plt.show()
            
            
def run_kmeans_on_iris(k):
    
    f = open('./data/iris.csv', 'r')
    raw_data = f.readlines()
    
    attributes = raw_data[0].split(',')
    
    for i in range(len(attributes)):
        attributes[i] = attributes[i].strip()[1:-1]
        
    samples = []
    for item in raw_data[1:]:
        sample = Sample(attributes)
        sample.set_attributes(item)
        samples.append(sample)
        # print(sample.data)

    plot_samples(samples, attributes[0], attributes[3])
    
    clusters = run_kmeans(samples, [attributes[0], attributes[3]], k)
    plot_clusters(clusters)
    
    
    

if __name__ == "__main__":
    f = open('iris.csv', 'r')
    raw_data = f.readlines()
    
    attributes = raw_data[0].split(',')
    
    for i in range(len(attributes)):
        attributes[i] = attributes[i].strip()[1:-1]
        
    samples = []
    for item in raw_data[1:]:
        sample = Sample(attributes)
        sample.set_attributes(item)
        samples.append(sample)
        # print(sample.data)

    plot_samples(samples, attributes[0], attributes[3])
    
    clusters = run_kmeans(samples, [attributes[0], attributes[3]], 3)
    plot_clusters(clusters)
    
        
    


