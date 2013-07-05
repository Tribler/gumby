import sys
import os
from jinja2 import Environment, FileSystemLoader
import csv

#THIS_DIR = os.path.dirname(os.path.abspath(__file__))
THIS_DIR = "../output/perf_reports/"
reportName = 'default'

def setReportName():
	global reportName	
	if len(sys.argv) > 1:
		reportName = sys.argv[1]
	else:
		print 'usage python make_io_writes_report.py reportName'
		exit()	

def readSummary():
	with file(THIS_DIR + reportName + '/summary.txt') as f:
		s = f.read()
	return s

def readDataframeDump(filename):
	var = []
	with open(filename, 'rb') as csvfile:
		reader = csv.DictReader(csvfile, delimiter = ',')
		for line in reader:
			var.append(line)		
	return var
	
def print_html_doc():
	loader = FileSystemLoader(searchpath = '../templates')
	env = Environment(loader=loader)
	template = env.get_template('template_io_writes_report.html')
	report = template.render(
		title= 'IO Writes Report',
		summary = readSummary(),
		top20PerStacktrace = readDataframeDump(THIS_DIR + reportName + '/top20_per_stacktrace.csv'),
		top20PerFilename = readDataframeDump(THIS_DIR + reportName + '/top20_per_filename.csv'),
		topLargestWrites = readDataframeDump(THIS_DIR + reportName + '/top_largest_writes.csv')
		
		
		)
	with open(THIS_DIR + reportName + '/io_writes_report.html', 'wb') as fh:
		fh.write(report)

 
if __name__ == '__main__':
	setReportName()
	print_html_doc()

