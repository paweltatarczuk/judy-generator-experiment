#!/usr/bin/python

import csv
import os
from os import path
import re
import sys
import signal
import subprocess
from threading import Timer
import xml.etree.ElementTree as ET

class TimeoutException(Exception):
	pass

def get_projects():
	"""Returns projects for processing"""
	if len(sys.argv) > 1:
		return [Project(name) for name in sys.argv[1:]]

	return Project.list_projects()

def log(msg):
	"""Log message to console"""
	print msg

def ant(task, reportpath, args = []):
	"""Perform ant task"""
	log("Running ant %s task for %s" % (task, task.project))
	args = ["ant", task.name] + args

	f = open(reportpath, "w")
	cmd = ["bash", "-c", ("cd %s && " % task.project) + " ".join(args)]

	def kill(proc):
		print "Timeout"
		subprocess.call(["pkill", "-P", str(proc.pid)])

	proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
	timer = Timer(300, kill, [proc])
	try:
		timer.start()
		proc.communicate()
	finally:
		timer.cancel()

	if proc.returncode != 0:
		raise subprocess.CalledProcessError(proc.returncode, cmd, None)

class Task(object):
	"""Task class"""

	name = ""
	steps = 1
	check = True

	def __init__(self, project):
		self.project = project

	def __str__(self):
		return self.name

	def log_path(self, step=None):
		"""Return log path"""
		name = self.name + "-" +str(step)
		return path.join(self.project.path, "report", "log", name)

	def run(self):
		"""Run task"""

		for step in range(1, self.steps + 1):
			try:
				self.run_one(step)
			except (subprocess.CalledProcessError, TimeoutException) as exc:
				if self.check is True:
					raise exc

	def run_one(self, step):
		"""Run single step"""
		args = ["-Dstep=" + str(step)]
		ant(self, self.log_path(step), args)

class JudyGenerateTestsTask(Task):
	name = "judy-generate-tests"

class EvosuiteGenerateTestsTask(Task):
	name = "evosuite-generate-tests"

class RandoopGenerateTestsTask(Task):
	name = "randoop-generate-tests"

class AnalysisTask(Task):

	target = "unknown"

	def __init__(self, project):
		self.project = project

		self.data = {}
		self.average = {}

		for classname in project.list_classes():
			self.average[classname] = {}

	def run_one(self, step):
		"""Collect analisys results after run"""
		super(AnalysisTask, self).run_one(step)
		self.data[step] = self.collect(step)

	def run(self):
		"""Collect results average for all steps"""
		super(AnalysisTask, self).run()

		# Combine all data
		combined = {}
		for step in self.data:
			combined[step] = combined[step] if step in combined else {}

			for classname in self.data[step]:
				combined[step][classname] = combined[step][classname] if classname in combined[step] else {}

				for key in self.data[step][classname]:
					combined[step][classname][key] = combined[step][classname][key] if key in combined[step][classname] else []
					combined[step][classname][key].append(self.data[step][classname][key])

		# Calculate averages
		for step in combined:
			for classname in combined[step]:
				for key in combined[step][classname]:
					values = combined[step][classname][key]

					if len(values) > 1:
						self.average[classname][key] = map(lambda x: x / len(values), reduce(lambda x, y: (int(x[0]) + int(y[0]), int(x[1]) + int(y[1])), values))
					else:
						self.average[classname][key] = values[0]

		self.project.add_stats({self.target: self.average})

class CoverageAnalysisTask(AnalysisTask):

	def collect(self, step):
		"""Collects coverage analysis results"""

		data = {}

		coverage_file = path.join(self.project.path, "report", "coverage", self.target, "report.csv")
		if path.isfile(coverage_file):
			with open(coverage_file, "rb") as csvfile:
				reader = csv.DictReader(csvfile, delimiter = ",")
				for row in reader:
					classname = row["PACKAGE"] + "." + re.sub(r'\..*', '', row["CLASS"])
					classname = re.sub(r'^default\.', '', classname)

					data[classname] = {}
					for key in ["instruction", "branch", "line", "complexity", "method"]:
						data[classname][key] = [
							int(row[key.upper() + "_COVERED"]),
							int(row[key.upper() + "_COVERED"]) + int(row[key.upper() + "_MISSED"])
						]

		return data

class EvosuiteAnalysisTask(AnalysisTask):

	def collect(self, step):
		"""Collects evosuite analysis results"""

		data = {}

		for classname in self.project.list_classes():
			evosuite_file = path.join(self.project.path, "report", "evosuite", self.target, classname + ".csv")
			if path.isfile(evosuite_file):
				with open(evosuite_file, "rb") as csvfile:
					reader = csv.DictReader(csvfile, delimiter = ",")
					row = reader.next()

					data[classname] = { "evosuite": [row["Covered_Goals"], row["Total_Goals"]] }

		return data

class JudyAnalysisTask(AnalysisTask):

	steps = 1

	def collect(self, step):
		"""Collects judy analysis results"""

		data = {}

		judy_file = path.join(self.project.path, "report", "judy", self.target + "-result-" + str(step) + ".xml")
		if path.isfile(judy_file):
			tree = ET.parse(judy_file)
			root = tree.getroot()

			classes = root.find("classes")
			if not classes == None:
				for c in classes.findall("class"):
					name = c.find("name")
					killed = c.find("mutantsKilledCount")
					mutants = c.find("mutantsCount")

					if (name is not None and killed is not None and mutants is not None):
						data[name.text] = { "judy": [killed.text, mutants.text] }

		return data

class JudyAnalyzeTestsTask(JudyAnalysisTask):
	name = "judy-analyze-tests"
	target = "tests"
	check = False

class JudyAnalyzeJudyTask(JudyAnalysisTask):
	name = "judy-analyze-judy"
	target = "judy"
	check = False

class JudyAnalyzeEvosuiteTask(JudyAnalysisTask):
	name = "judy-analyze-evosuite"
	target = "evosuite"
	check = False

class JudyAnalyzeRandoopTask(JudyAnalysisTask):
	name = "judy-analyze-randoop"
	target = "randoop"
	check = False

class EvosuiteAnalyzeTestsTask(EvosuiteAnalysisTask):
	name = "evosuite-analyze-tests"
	target = "tests"
	check = False

class EvosuiteAnalyzeJudyTask(EvosuiteAnalysisTask):
	name = "evosuite-analyze-judy"
	target = "judy"

class EvosuiteAnalyzeEvosuiteTask(EvosuiteAnalysisTask):
	name = "evosuite-analyze-evosuite"
	target = "evosuite"

class EvosuiteAnalyzeRandoopTask(EvosuiteAnalysisTask):
	name = "evosuite-analyze-randoop"
	target = "randoop"
	check = False

class CoverageAnalyzeTestsTask(CoverageAnalysisTask):
	name = "coverage-analyze-tests"
	target = "tests"
	check = False

class CoverageAnalyzeJudyTask(CoverageAnalysisTask):
	name = "coverage-analyze-judy"
	target = "judy"

class CoverageAnalyzeEvosuiteTask(CoverageAnalysisTask):
	name = "coverage-analyze-evosuite"
	target = "evosuite"

class CoverageAnalyzeRandoopTask(CoverageAnalysisTask):
	name = "coverage-analyze-randoop"
	target = "randoop"
	check = False

class Project:
	"""Project class"""

	def __init__(self, name):
		self.name = name
		self.path = path.join(os.getcwd(), name)
		self.stats = {}

	def __str__(self):
		return self.name

	@staticmethod
	def list_projects():
		"""Lists projects in current working directory"""
		pattern = r'^(\d+)_'
		projects = [filename for filename in os.listdir(".") if re.match(pattern, filename)]

		def key(value):
			"""Key function"""
			return int(re.match(pattern, value).group(1))

		return [Project(name) for name in sorted(projects, key=key)]

	def list_classes(self):
		"""List all available classes in project"""
		f = open(path.join(self.path, 'class.list'), 'r')
		return map(str.strip, f.readlines())

	def process(self):
		"""Processes project"""
		if not path.exists(path.join(self.path, "report", "log")):
			os.makedirs(path.join(self.path, "report", "log"))
		log("Starting experiment for: %s" % self)

		generation_tasks = [
			JudyGenerateTestsTask(self),
			EvosuiteGenerateTestsTask(self),
			RandoopGenerateTestsTask(self),
		]

		analysis_tasks = [
			JudyAnalyzeTestsTask(self),
			EvosuiteAnalyzeTestsTask(self),
			CoverageAnalyzeTestsTask(self),
			JudyAnalyzeJudyTask(self),
			EvosuiteAnalyzeJudyTask(self),
			CoverageAnalyzeJudyTask(self),
			JudyAnalyzeEvosuiteTask(self),
			EvosuiteAnalyzeEvosuiteTask(self),
			CoverageAnalyzeEvosuiteTask(self),
			JudyAnalyzeRandoopTask(self),
			EvosuiteAnalyzeRandoopTask(self),
			CoverageAnalyzeRandoopTask(self),
		]

		# Run tasks
		for task in generation_tasks + analysis_tasks:
			task.run()

	def add_stats(self, stats):
		"""Add project stats"""
		for key in stats:
			if key not in self.stats:
				self.stats[key] = {}

			self.stats[key].update(stats[key])

	@staticmethod
	def format_result(result):
		"""Format a result [X, Y] to a percantage number"""
		if result[1] == 0:
			return "NaN"

		return "%1.2f" % (float(result[0]) / float(result[1]))

	def print_results(self):
		"""Get project results"""
		print "Project %s\n" % self.name
		for target in self.stats:
			print "--- Results for %s tests:" % target
			print "%60s %6s %13s %12s %8s %8s %10s %6s" % (
				"class",
				"line",
				"instruction",
				"complexity",
				"branch",
				"method",
				"evosuite",
				"judy",
			)
			for classname in self.stats[target]:
				stats = self.stats[target][classname]
				print "%60s %6s %13s %12s %8s %8s %10s %6s" % (
					classname,
					"-" if "line" not in stats else self.format_result(stats["line"]),
					"-" if "instruction" not in stats else self.format_result(stats["instruction"]),
					"-" if "complexity" not in stats else self.format_result(stats["complexity"]),
					"-" if "branch" not in stats else self.format_result(stats["branch"]),
					"-" if "method" not in stats else self.format_result(stats["method"]),
					"-" if "evosuite" not in stats else self.format_result(stats["evosuite"]),
					"-" if "judy" not in stats else self.format_result(stats["judy"]),
				)
			print "\n"

def run():
	"""Processes projects"""
	projects = get_projects()

	for project in projects:
		project.process()
		project.print_results()

run()
