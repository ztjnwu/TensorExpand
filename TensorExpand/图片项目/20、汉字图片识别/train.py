# -*- coding: UTF-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import tensorflow as tf
from tensorflow.contrib import slim
import numpy as np
from glob import glob
from PIL import Image
import os

def tfrecord_to_numpy(file_path,img_pixel=64,batch_size=64):
    '''
    加载tfrecord文件
    :param file_path: tfrecord文件路径
    :param img_pixel: 样本像素大小
    :param batch_size: 每批次训练的样本数
    :return: 
    '''
    filename_queue = tf.train.string_input_producer(
        tf.train.match_filenames_once(file_path))  # 加载多个Tfrecode文件
    reader = tf.TFRecordReader()
    _, serialized = reader.read(filename_queue)

    features = tf.parse_single_example(
        serialized,
        features={
            # 'label': tf.FixedLenFeature([], tf.string),
            'label': tf.FixedLenFeature([], tf.int64),
            'image': tf.FixedLenFeature([], tf.string),
        })

    record_image = tf.decode_raw(features['image'], tf.float16)
    image = tf.reshape(record_image, [img_pixel, img_pixel])
    label = tf.cast(features['label'], tf.int64)
    # label = tf.cast(features['label'], tf.string)

    min_after_dequeue = 1000
    capacity = min_after_dequeue + batch_size
    data, label = tf.train.shuffle_batch(
        [image, label], batch_size=batch_size, capacity=capacity,
        min_after_dequeue=min_after_dequeue
    )

    # 将图像转换为灰度值位于[0,1)的浮点类型，
    # float_image_batch = tf.image.convert_image_dtype(data, tf.float32)
    # return float_image_batch, label
    return data,label

# 设置超参数
num_class=3755
image_size=64
learning_rate=1e-5
epochs=1
train=1 # 1 train,0 test
batch_size=128
keep=0.8
logdir='./checkpoint/'

x=tf.placeholder(tf.float32,[None,image_size,image_size])
y_=tf.placeholder(tf.int64,[None,])
keep_rate=tf.placeholder(tf.float32)
is_training=tf.placeholder(tf.bool)


# 搭建网络
net=tf.expand_dims(x,-1) # [n,64,64,1]
net=tf.layers.conv2d(net,64,5,padding='same',name='conv1')
# net=tf.layers.batch_normalization(net,is_training=is_training)
net=slim.batch_norm(net,is_training=is_training)
net=tf.nn.leaky_relu(net)
net=slim.max_pool2d(net,2,2,'same') # [n,32,32,64]

net=tf.layers.conv2d(net,128,5,padding='same',name='conv2')
# net=tf.layers.batch_normalization(net,is_training=is_training)
net=slim.batch_norm(net,is_training=is_training)
net=tf.nn.leaky_relu(net)
net=slim.max_pool2d(net,2,2,'same') # [n,16,16,128]

net=tf.layers.conv2d(net,256,5,padding='same',name='conv3')
# net=tf.layers.batch_normalization(net,is_training=is_training)
net=slim.batch_norm(net,is_training=is_training)
net=tf.nn.leaky_relu(net)
net=slim.max_pool2d(net,2,2,'same') # [n,8,8,256]

net=tf.layers.conv2d(net,512,5,padding='same',name='conv4')
# net=tf.layers.batch_normalization(net,is_training=is_training)
net=slim.batch_norm(net,is_training=is_training)
net=tf.nn.leaky_relu(net)
net=slim.max_pool2d(net,2,2,'same') # [n,4,4,512]

net=tf.layers.conv2d(net,1024,5,padding='same',name='conv5')
# net=tf.layers.batch_normalization(net,is_training=is_training)
net=slim.batch_norm(net,is_training=is_training)
net=tf.nn.leaky_relu(net)
net=slim.max_pool2d(net,2,2,'same') # [n,2,2,1024]

net=tf.layers.conv2d(net,num_class,5,padding='same',name='conv6')
# net=tf.layers.batch_normalization(net,is_training=is_training)
net=slim.batch_norm(net,is_training=is_training)
net=tf.nn.leaky_relu(net)
net=slim.max_pool2d(net,2,2,'same') # [n,1,1,3755]

net=tf.reshape(net,[-1,num_class])
net=slim.dropout(net,keep_rate,is_training=is_training)

prediction=slim.softmax(net) # [n,3755]

# Define loss and optimizer
cost = tf.reduce_mean(tf.nn.sparse_softmax_cross_entropy_with_logits(logits=prediction, labels=y_))
optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(cost)

# Evaluate model
correct_pred = tf.equal(tf.argmax(prediction, 1), y_)
accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))


if __name__=="__main__":
    sess = tf.InteractiveSession()

    if train==1:
        x_train_batch, y_train_batch = tfrecord_to_numpy('./data/train-*.tfrecords')
        steps = 895035 // batch_size
    if train==0:
        x_test_batch, y_test_batch = tfrecord_to_numpy('./data/test-*.tfrecords')
        i = 0
        acc_list = []
    # print(x_train_batch.shape)
    # print(y_train_batch.shape)

    init = tf.group(tf.global_variables_initializer(), tf.local_variables_initializer())
    sess.run(init)

    saver=tf.train.Saver(tf.global_variables())

    # 验证之前是否已经保存了检查点文件
    ckpt = tf.train.get_checkpoint_state(logdir)
    if ckpt and ckpt.model_checkpoint_path:
        saver.restore(sess, ckpt.model_checkpoint_path)

    if not os.path.exists(logdir):os.mkdir(logdir)

    # print(sess.run(y_train_batch))

    coord = tf.train.Coordinator()
    threads = tf.train.start_queue_runners(sess=sess, coord=coord)

    try:
        while not coord.should_stop():

            if train==1: # 训练
                # Run training steps or whatever
                # print(curr_x_train_batch[0])
                # print(np.max(curr_x_train_batch[0]))
                # exit(0)
                for epoch in range(epochs):
                    for step in range(steps):
                        curr_x_train_batch, curr_y_train_batch = sess.run([x_train_batch, y_train_batch])
                        optimizer.run({x:curr_x_train_batch,y_:curr_y_train_batch,keep_rate:keep,is_training:True})
                        if step %100==0:
                            acc=accuracy.eval({x:curr_x_train_batch,y_:curr_y_train_batch,keep_rate:1.,is_training:True})
                            print('epoch',epoch,'|','step',step,'|','acc',acc)

                    saver.save(sess, logdir + 'model.ckpt',global_step=epoch)
                break

            if train==0: # 测试
                curr_x_test_batch, curr_y_test_batch = sess.run([x_test_batch, y_test_batch])
                acc = accuracy.eval({x: curr_x_test_batch, y_: curr_y_test_batch, keep_rate: 1., is_training: True})
                acc_list.append(acc)

                if i % 100 == 0:
                    print('step', i, '|', 'acc', acc)
                i += 1

    except tf.errors.OutOfRangeError:
        print('test acc', np.mean(acc_list))
        print('Done training -- epoch limit reached')

    finally:
        # When done, ask the threads to stop.
        coord.request_stop()
    # Wait for threads to finish.
    coord.join(threads)
    sess.close()