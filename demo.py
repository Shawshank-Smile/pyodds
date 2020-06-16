import numpy as np
import argparse
import time
import logging
import getpass
import warnings
from pyodds.utils.utilities import output_performance,insert_demo_data,connect_server,query_data
from pyodds.utils.importAlgorithm import algorithm_selection
from pyodds.utils.plotUtils import visualize_distribution_static,visualize_distribution_time_serie,visualize_outlierscore,visualize_distribution
from pyodds.utils.utilities import str2bool
from pyodds.automl.cash import Cash
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.simplefilter("ignore", UserWarning)
logging.disable(logging.WARNING)

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Anomaly Detection Platform Settings")
    #TDengine server IP
    parser.add_argument('--host', default='127.0.0.1')
    #TDengine username，default：root
    parser.add_argument('--user', default='username')
    parser.add_argument('--random_seed',default=42, type=int)
    #TDengine db
    parser.add_argument('--database',default='db')
    parser.add_argument('--table',default='t')
    parser.add_argument('--time_stamp',const=True,type=str2bool,nargs='?')
    parser.add_argument('--visualize_distribution',default=True,const=True,type=str2bool,nargs='?')
    parser.add_argument('--algorithm',default='dagmm',choices=['iforest','lof','ocsvm','robustcovariance','staticautoencoder','luminol','cblof','knn','hbos','sod','pca','dagmm','autoencoder','lstm_ad','lstm_ed'])
    parser.add_argument('--contamination',default=0.05)
    parser.add_argument('--start_time',default='2019-07-20 00:00:00')
    parser.add_argument('--end_time',default='2019-08-20 00:00:00')
    parser.add_argument('--time_serie_name',default='ts')
    parser.add_argument('--ground_truth',default=True,const=True,type=str2bool,nargs='?')
    parser.add_argument('--saving_path',default='./output/img')


    args = parser.parse_args()

    #random seed setting
    rng = np.random.RandomState(args.random_seed)
    np.random.seed(args.random_seed)

    #TDengine password，default：taosdata
    password = getpass.getpass("Please input your password:")

    #connection configeration
    conn,cursor=connect_server(args.host, args.user, password)

    #read data
    print('Load dataset and table')
    start_time = time.clock()
    if args.ground_truth:
        ground_truth_whole=insert_demo_data(conn,cursor,args.database,args.table,args.ground_truth)
    else:
        insert_demo_data(conn,cursor,args.database,args.table,args.ground_truth)

    if args.ground_truth:
        data,ground_truth = query_data(conn,cursor,args.database,args.table,
                                   args.start_time,args.end_time,args.time_serie_name,ground_truth_whole,time_serie=args.time_stamp,ground_truth_flag=args.ground_truth)
    else:
        data = query_data(conn,cursor,args.database,args.table,
                                   args.start_time,args.end_time,args.time_serie_name,time_serie=args.time_stamp,ground_truth_flag=args.ground_truth)

    print('Loading cost: %.6f seconds' %(time.clock() - start_time))
    print('Load data successful')

    #Algorithm Selection
    if args.ground_truth:
        alg_selector = Cash(data, ground_truth)
        clf = alg_selector.model_selector(max_evals=2)
    else:
        clf = algorithm_selection(args.algorithm,random_state=rng,contamination=args.contamination)

    start_time = time.clock()
    clf.fit(data)
    prediction_result = clf.predict(data)
    outlierness = clf.decision_function(data)
    anomaly_scores = clf.anomaly_likelihood(data)

    if args.ground_truth:
        output_performance(args.algorithm,ground_truth,prediction_result,time.clock() - start_time,anomaly_scores)

    if args.visualize_distribution and args.ground_truth:
        if not args.time_stamp:
            visualize_distribution_static(data,prediction_result,outlierness,args.saving_path)
            visualize_distribution(data,prediction_result,outlierness,args.saving_path)
            visualize_outlierscore(outlierness,prediction_result,args.contamination,args.saving_path)
        else:
            visualize_distribution_time_serie(clf.ts,data,args.saving_path)
            visualize_outlierscore(outlierness,prediction_result,args.contamination,args.saving_path)

    conn.close()
