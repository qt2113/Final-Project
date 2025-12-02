from sample import Sample, plot_samples
from matplotlib import pyplot as plt


LABELS = ('Setosa', 'Versicolor', 'Virginica')
COLORS = {"Setosa": 'r', "Versicolor": 'g', "Virginica": 'b'}
SHAPES = {"Setosa": 'v', "Versicolor": 'o', "Virginica": 'x'}



def knn(p, data, k):
    """ Compute the distance between p to every sample in data,
        set p's label to the label of the maximum of samples
        within the k nearest neighbors

        # p is a SAMPLE object
        # data is a list of SAMPLE object
        # k is int
    """

    """ Steps:
        1. Iterate through samples in data and store the
           distance from p in the dictionary "distance"; key is the
           distance, value is the sample.
        2. Creat a sorted list of samples according to ascending
           order of the distances.
        3. In the dictioary "label_votes", stores number of votes
           in each label among the top-k nearest samples
        4. Assign p the most popular label
    """
    distances = {} #dict of distance
    ##--below, input your code for computeing the distance--##
    for d in data:
        if d.distance(p) not in distances.keys():
            distances[d.distance(p)] = [ d ]
        else:
            distances[d.distance(p)].append(d)
    
    ##--end of your code--##
    
    sorted_samples = [] #the sorted list of samples in data
    ##--below, input your code for sortig the samples--##
    for key in sorted(distances.keys()):
        sorted_samples.extend(distances[key])
    
    k_nearest_neighbors = sorted_samples[:k]
    # print(k_nearest_neighbors)
    
    ##--end of your code--##
     
    label_votes = { l:0 for l in LABELS } #dict of votes per label
    ##--below, input your code for finding the max label--##
    # print(p.data)
    
    for x in k_nearest_neighbors:
        # print('x', x.data)
        label_votes[x.get_label()] += 1
    
    print("label_votes", label_votes)
    max_label = sorted(label_votes, key=label_votes.get, reverse=True)[0]
    print("max", max_label)
    # max_label = util.LABELS[0] #modify it to a correct expression
    ## above forces a fixed label: remove them
    ##--end of your code--##
    p.set_label(max_label)
    

if __name__ == "__main__":
    # load data   
    f = open('iris.csv', 'r')
    raw_data = f.readlines()
   
    raw_data = [item.strip().split(",") for item in raw_data]
    # print(raw_data)
        
    data = []
    for item in raw_data[1:]: #ignore the first row
        sample = Sample(float(item[0]), float(item[1]), label=item[-1][1:-1])
        data.append(sample)
        
    K = 3
    def onclick(event):
        # Creating a new point and finding the k nearest neighbours
        new = Sample(event.xdata, event.ydata)
        knn(new, data, K)
        # draw the new point
        data.append(new)
        plt.scatter(event.xdata, event.ydata, \
                      label = new.get_label(), \
                      marker = SHAPES[new.get_label()], \
                      color = COLORS[new.get_label()])
        plt.draw()
    # start plotting
    fig = plt.figure()
    cid = fig.canvas.mpl_connect('button_press_event', onclick)  
    plot_samples(data)
   