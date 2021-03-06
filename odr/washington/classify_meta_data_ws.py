#!/usr/bin/env python
import caffe
from svmutil import *

import numpy as np
from PIL import Image
from scipy import misc, io
import shutil

import GPy

import os
import time
import cv2
import sys

from tqdm import tqdm


def extract_feature( dir ):
	global caffe 
	global rgb_net
	global depth_net
	global mode
	global feat

	width = 224
	height = 224

	if mode == 'cpu':
		caffe.set_mode_cpu()
	else:
		caffe.set_device(0)
		caffe.set_mode_gpu()


	if feat == 'rgb' or feat == 'depth':
		D = 4096
	else:
		D = 4096*2

	N = len(os.listdir( dir ))

	feature = np.zeros([N/2,D])
	files = []

	count = 0

	for file in tqdm(os.listdir( dir )):

		if file.endswith( ".jpg" ) or file.endswith( ".png" ) or file.endswith( ".jpeg" ):
			#print( 'extracting feature from ' + dir + '/' + os.path.splitext(file)[0] + '...' + str(count) + " of " + str(N) )

			if feat == 'rgb' or feat == 'rgbd':

				#print "extracting rgb feature ..."
				
				rgb = Image.open( dir + '/' + file )
				rgb = misc.imresize( rgb, (width,height) )
				np_rgb = np.array( rgb, dtype=np.float32 )

				if len(np_rgb.shape) == 2 or np_rgb.shape[2] != 3:
					continue

				# convert rgb to bgr
				np_rgb = np_rgb[:,:,::-1]
				# substract the mean
				np_rgb -= np.array( (104.00698793,116.66876762,122.67891434) )

				# transpose
				np_rgb = np_rgb.transpose( (2,0,1) )

				# shape for input (data blob is 1 x C x H x W), set data
				rgb_net.blobs['data'].reshape(1, *np_rgb.shape)
				rgb_net.blobs['data'].data[...] = np_rgb

				start_time = time.time()
				rgb_net.forward()
				#print(time.time()-start_time)

				# get the feature blob
				rgb_feat_fc7 = np.array( rgb_net.blobs['fc7'].data, dtype=np.float32 )
				#print rgb_feat_fc7.shape

			if feat == 'depth' or feat == 'rgbd':

				#print "extracting depth feature ..."

				mat = io.loadmat('{}/{}.{}'.format(dir, os.path.splitext(file)[0], 'mat'))
				np_depth = mat['depth_map'].astype(np.double)
				np_depth = cv2.resize( np_depth, (width,height) )

				# substract the mean
				np_depth -= np.array( 2 )

				# transpose
				np_depth = np_depth[np.newaxis, ...]

				# shape for input (data blob is 1 x C x H x W), set data
				depth_net.blobs['data'].reshape(1, *np_depth.shape)
				depth_net.blobs['data'].data[...] = np_depth

				start_time = time.time()
				depth_net.forward()
				#print(time.time()-start_time)

				# get the feature blob
				depth_feat_fc7 = np.array( depth_net.blobs['fc7'].data, dtype=np.float32 )
				#print depth_feat_fc7.shape

			
			if feat == 'rgb':
				feat_fc7 = rgb_feat_fc7
			elif feat == 'depth':
				feat_fc7 = depth_feat_fc7
			elif feat == 'rgbd':
				feat_fc7 = np.concatenate( (rgb_feat_fc7, depth_feat_fc7), 1 )
			else:
				print "ERROR: unknown feature mode"

			#print feat_fc7.shape

			if feature.size == 0:
				#feature = feat_fc7
				feature[count,:] = feat_fc7
				files.append(file)
			else:
				#feature = np.concatenate( (feature, feat_fc7), 0 )
				feature[count,:] = feat_fc7
				files.append(file)

			count = count + 1

	return feature, files

def gp_load_model(dirX='gp_model_X.npy', dirY='gp_model_Y.npy', dirParam='gp_model_param.npy'):
	# loading a model
	# Model creation, without initialization:
	X = np.load(dirX)
	Y = np.load(dirY)

	opt = "rgbd"

	if opt == "rgbd":
		k_rgb = GPy.kern.RBF(X.shape[1]/2,variance=50,lengthscale=90, active_dims=np.arange(0,4096))
		k_depth = GPy.kern.RBF(X.shape[1]/2,variance=80,lengthscale=35, active_dims=np.arange(4096,8192))
		k = k_rgb * k_depth
	elif opt == "linear":
		k = GPy.kern.Linear(X.shape[1], active_dims=None, ARD=True)
	elif opt == "rbf":
		k = GPy.kern.RBF(X.shape[1], variance=50,lengthscale=90, active_dims=None)


	f = np.random.multivariate_normal(np.zeros(X.shape[0]), k.K(X))
	lik = GPy.likelihoods.Bernoulli()

	gp_model = GPy.core.GP(X=X,
                Y=Y, 
                kernel=k, 
                inference_method=GPy.inference.latent_function_inference.laplace.Laplace(), #expectation_propagation.EP(),
                likelihood=lik)


	#gp_model = GPy.models.GPClassification(X, Y, initialize=False)
	gp_model.update_model(False) # do not call the underlying expensive algebra on load
	gp_model.initialize_parameter() # Initialize the parameters (connect the parameters up)
	gp_model.param_array[:] = np.load('gp_model_param.npy') # Load the parameters
	gp_model.update_model(True) # Call the algebra only once
	print(gp_model)

	return gp_model


def gp_train(X, Y):

	k = GPy.kern.RBF(X.shape[1],variance=250,lengthscale=250)
	print k.K(X)

	io.savemat('./kernel.mat', {'K':np.array(k.K(X))})

	f = np.random.multivariate_normal(np.zeros(X.shape[0]), k.K(X))
	lik = GPy.likelihoods.Bernoulli()

	m = GPy.core.GP(X=X,
                Y=Y, 
                kernel=k, 
                inference_method=GPy.inference.latent_function_inference.expectation_propagation.EP(),
                likelihood=lik)

	for i in range(5):
		m.optimize('bfgs', max_iters=100) #first runs EP and then optimizes the kernel parameters
		print 'iteration:', i,
		print m
		print ""

	print m

	return m


def main():

	global caffe
	global rgb_net
	global depth_net
	global mode
	global feat

	num1 = 100
	num2 = 500
	threshold = 0.5

	#------------------------------------- setting ---------------------------------------------------------
	mode = sys.argv[1]
	feat = str(sys.argv[2])
	cat = str(sys.argv[3])

	classifier = "gp"

	print "-------------------------------------"
	print "caffe mode is: " + mode
	print "feature mode is: " + feat
	print "classifier is: " + classifier
	print "category is: " + cat
	print "-------------------------------------"


	if mode == 'cpu':
		caffe.set_mode_cpu()
	else:
		caffe.set_device(0)
		caffe.set_mode_gpu()

	if feat == 'rgb' or feat == 'rgbd':
		rgb_net = caffe.Net('/home/kevin/models/vgg16/deploy.prototxt', '/home/kevin/models/vgg16/model.caffemodel', caffe.TEST)
	if feat == 'depth' or feat == 'rgbd':
		depth_net = caffe.Net('/home/kevin/models/model_net/heavy/deploy.prototxt', '/home/kevin/models/model_net/heavy/model.caffemodel', caffe.TEST)
	
		
	unlabelled_data_dir = '/home/kevin/dataset/ws_exp/unlabelled'

	labelled_data_dir = '/home/kevin/dataset/ws_exp/labelled'

	gp_labelled_data_dir = '/home/kevin/dataset/ws_exp/gp_labelled'

	
	folder = [ cat ]

	for folderi in folder:
		if os.path.isdir(os.path.join(gp_labelled_data_dir, folderi)) == False:
			os.mkdir(os.path.join(gp_labelled_data_dir, folderi))

	#------------------------------------GP labelling---------------------------------------------------------------------

	instances = np.array( [] )
	files = []


	for foldi in folder:

		gp_model = gp_load_model()

		instance_i, files_i = extract_feature( os.path.join(unlabelled_data_dir) ) 

		if instances.size == 0:
			instances = instance_i
			files = files_i
		else:
			instances = np.concatenate( ( instances, instance_i ), 0 )
			files = files + files_i

	
		print instances.shape
		print len(files)

		probs = gp_model.predict(instances)[0]

		# sorting depending on predictive probality (perception confidence)
		sorted_probs = np.sort(probs.flatten())
		index = np.argsort(probs.flatten())

		# select upto num instances
		sorted_probs = sorted_probs[-num2:]
		index = index[-num2:]

		# change selected list to descending order
		sorted_probs = sorted_probs[::-1] 
		index = index[::-1]

		print sorted_probs

		print sorted_probs.shape
		print index.shape

		count = 0
		for sp, idx in zip(sorted_probs,index):
			if sp > threshold:
				src = os.path.join(unlabelled_data_dir, files[idx])
				dst = os.path.join(gp_labelled_data_dir, foldi, files[idx])
				print src
				print dst
				shutil.copy(src, dst)

				src = '{}/{}.{}'.format(unlabelled_data_dir, os.path.splitext(files[idx])[0], 'mat')
				dst = '{}/{}/{}.{}'.format(gp_labelled_data_dir, foldi, os.path.splitext(files[idx])[0], 'mat')

				print src
				print dst
				shutil.copy(src, dst)

				print "confidence is " + str(sp)

				count = count + 1

		if count < num1:

				for sp, idx in zip(sorted_probs,index):
					if count < num1:
						src = os.path.join(unlabelled_data_dir, files[idx])
						dst = os.path.join(gp_labelled_data_dir, foldi, files[idx])
						print src
						print dst
						shutil.copy(src, dst)

						src = '{}/{}.{}'.format(unlabelled_data_dir, os.path.splitext(files[idx])[0], 'mat')
						dst = '{}/{}/{}.{}'.format(gp_labelled_data_dir, foldi, os.path.splitext(files[idx])[0], 'mat')

						print src
						print dst
						shutil.copy(src, dst)

						print "confidence is " + str(sp)

						count = count + 1
			

		print str(count) + " instance are labelled by GP"
	



if __name__ == "__main__": main()
