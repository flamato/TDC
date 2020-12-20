import pandas as pd
import numpy as np
import os, sys, json 
import warnings
warnings.filterwarnings("ignore")

from .utils import *
from .metadata import get_task2category
from .evaluator import Evaluator

class BenchmarkGroup:
	def __init__(self, name, path = './data'):
		'''
		-- PATH
			-- ADMET_Benchmark
				-- HIA_Hou
					-- train.csv
					-- valid.csv
					-- test.csv
				-- Caco2_Wang
					-- train.csv
					-- valid.csv
					-- test.csv
				....
		from tdc import BenchmarkGroup
		group = BenchmarkGroup(name = 'ADMET_Group', path = 'data/')
		predictions = {}

		for benchmark in group:
		   name = benchmark['name']
		   train, valid, test = benchmark['train'], benchmark['valid'], benchmark['test']
		   ## --- train your model --- ##
		   predictions[name] = y_pred

		group.evaluate(predictions)
		# {'caco2_wang': 0.234, 'hia_hou': 0.786}

		benchmark = group.get('Caco2_Wang')
		train, valid, test = benchmark['train'], benchmark['valid'], benchmark['test']
		## --- train your model --- ##
		group.evaluate(y_pred, benchmark = 'Caco2_Wang')
		# 0.234

		group.get_more_splits()
		'''
		
		task2category = get_task2category()
		name = fuzzy_search(name, retrieve_all_benchmarks())
		self.name = name
		self.datasets = retrieve_benchmark_names(name)

		# create a benchmark folder
		if not os.path.exists(path):
			os.mkdir(path)
		self.benchmark_path = os.path.join(path, name+'_benchmark')
		if not os.path.exists(self.benchmark_path):
			os.mkdir(self.benchmark_path)

		self.dataloaders = {}
		# get data set local copy
		for task, datasets in self.datasets.items():
			category = task2category[task]
			# import the task
			exec('from .' + category + ' import ' + task)
			for dataset in datasets:
				print_sys('--- ' + dataset + ' ---')
				dataset_path = os.path.join(self.benchmark_path, dataset)

				if not os.path.exists(dataset_path):
					os.mkdir(dataset_path)
				data_ = eval(task + '(name = \'' + dataset + '\', path = \'' + path + '\')')
				
				self.dataloaders[dataset] = data_

				if not os.path.exists(os.path.join(dataset_path, 'train.csv')):
					
					if name == 'admet_group':
						out = data_.get_split(method = 'scaffold', seed = 42, frac = [0.7, 0.1, 0.2])
					else:
						out = data_.get_split()
					
					out['train'].to_csv(os.path.join(dataset_path, 'train.csv'), index = False)
					out['valid'].to_csv(os.path.join(dataset_path, 'valid.csv'), index = False)
					out['test'].to_csv(os.path.join(dataset_path, 'test.csv'), index = False)
				else:
					print_sys('Local split is found for ' + dataset + '...')
		self.all_datasets = list(self.dataloaders.keys())

	def __iter__(self):
		self.index = 0
		self.num_datasets = len(self.all_datasets)
		return self

	def __next__(self):
		if self.index < self.num_datasets:
			dataset = self.all_datasets[self.index]
			print_sys('--- ' + dataset + ' ---')
			data_path = os.path.join(self.benchmark_path, dataset)
			train = pd.read_csv(os.path.join(data_path, 'train.csv'))
			valid = pd.read_csv(os.path.join(data_path, 'valid.csv'))
			test = pd.read_csv(os.path.join(data_path, 'test.csv'))
			self.index += 1
			return {'train': train, 'valid': valid, 'test': test, 'name': dataset}
		else:
			raise StopIteration
			
	def get_more_train_val_splits(self, seed = 42):
		raise NotImplementedError

	def get(self, benchmark):
		pass

	def evaluate(self, pred, true = None, benchmark = 'all'):
		'''
		When benchmark is set to all, it expects the pred to be a dictionary with key: benchmark name and value: prediction array on test set
		When benchmark is individual dataset name, the pred is just an array of prediction scores.
		'''
		metric_dict = metric_names[self.name]
		if benchmark == 'all':
			out = {}
			for data_name, pred_ in pred.items():
				data_name = fuzzy_search(data_name, self.all_datasets)
				data_path = os.path.join(self.benchmark_path, data_name)
				test = pd.read_csv(os.path.join(data_path, 'test.csv'))
				y = test.Y.values
				exec('evaluator = Evaluator(name = ' + metric_dict[data_name] + ')')
				out[data_name] = {metric_dict[data_name]: evaluator(y, pred_)}
		else:
			data_name = fuzzy_search(benchmark, self.all_datasets)
			data_path = os.path.join(self.benchmark_path, data_name)
			test = pd.read_csv(os.path.join(data_path, 'test.csv'))
			y = test.Y.values
			exec('evaluator = Evaluator(name = ' + metric_dict[data_name] + ')')
			return {metric_dict[data_name]: evaluator(y, pred)}