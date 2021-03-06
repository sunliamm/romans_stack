import numpy as np
import matplotlib.pyplot as plt
import caffe

caffe.set_mode_gpu()

# Load the original network and extract the fully connected layers' parameters.
net1 = caffe.Net('/home/kevin/models/vgg16/deploy.prototxt', 
                '/home/kevin/models/vgg16/model.caffemodel', 
                caffe.TEST)
params1 = ['conv1_1', 'conv1_2', 'conv2_1', 'conv2_2', 'conv3_1', 'conv3_2', 'conv3_3', 'conv4_1', 'conv4_2', 'conv4_3', 'conv5_1', 'conv5_2', 'conv5_3', 'fc6', 'fc7']
#fc_params = {name: (weights, biases)}
params_net1 = {pr: (net1.params[pr][0].data, net1.params[pr][1].data) for pr in params1}

print "====================================================================================="
print "finish loading the source model"
print "====================================================================================="

for pr in params1:
	print 'fc: {} weights are {} dimensional and biases are {} dimensional'.format(pr, params_net1[pr][0].shape, params_net1[pr][1].shape)
	

net2 = caffe.Net('train.prototxt', 
                '/home/kevin/models/vgg16/model.caffemodel', 
                caffe.TEST)
params2 = ['conv1_1', 'conv1_2', 'conv2_1', 'conv2_2', 'conv3_1', 'conv3_2', 'conv3_3', 'conv4_1', 'conv4_2', 'conv4_3', 'conv5_1', 'conv5_2', 'conv5_3', 'rgb_fc6', 'rgb_fc7']
#conv_params = {name: (weights, biases)}
params_net2 = {pr: (net2.params[pr][0].data, net2.params[pr][1].data) for pr in params2}

print "====================================================================================="
print "finish loading the target model"
print "====================================================================================="

for pr in params2:
    print 'net2: {} weights are {} dimensional and biases are {} dimensional'.format(pr, params_net2[pr][0].shape, params_net2[pr][1].shape)


# transplant the weights
for pr1, pr2 in zip(params1, params2):
    print "------------------------->"
    print "------------------------->"
    print "------------------------->"
    print "copy " 
    print params_net1[pr1][0].shape
    print "to "
    print params_net2[pr2][0].shape
    print "------------------------->"
    print "------------------------->"
    print "------------------------->"
    print "copy " 
    print params_net1[pr1][1].shape
    print "to "
    print params_net2[pr2][1].shape

    params_net2[pr2][0][...] = params_net1[pr1][0] 
    params_net2[pr2][1][...] = params_net1[pr1][1]

print "save new caffemodel"
net2.save('/home/kevin/models/rgbd_net/model.caffemodel')

print "====================================================================================="
