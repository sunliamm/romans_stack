#!/usr/bin/python
# -*- coding: utf-8 -*-
# @Author: Kevin Sun
# @Date:   2016-11-03 18:35:52
# @Last Modified by:   Kevin Sun
# @Last Modified time: 2016-11-06 05:34:28


import caffe
import score
import numpy as np


weights = '/home/kevin/models/rgbd_net/romans/romans_fast_stage1_model.caffemodel'

weights = '/home/kevin/snapshot/romans_fast_stage1_iter_10000.caffemodel'

# init
caffe.set_device(0)
caffe.set_mode_gpu()

solver = caffe.SGDSolver('solver.prototxt')
solver.net.copy_from(weights)

test_list = np.loadtxt('/home/kevin/dataset/rgbd/test.txt', dtype=str)

for i in range(10):
	solver.step(1000)
	score.model_classification_test(solver, '/home/kevin/tmp/'.format(i), test_list, layer='fc8', gt='label')

