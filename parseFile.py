# This iterates though the raw HTML files downloaded from
# Classie-Evals parses them into JSON files

from bs4 import BeautifulSoup
import re
import json
import os


def main():
	fileName = 'Parsed Data/courseData '
	fileType = '.json'
	batchSize = 500

	writeFile = open(fileName + '0' + fileType, 'w+')
	for num, readFile in enumerate(os.listdir("Raw Data")):
		myClass = parseFile("Raw Data/" + readFile)
		writeFile.write(json.dumps(myClass) + '\n')
		if (num + 1) % batchSize == 0:
			currentCount = int((num + 1) / batchSize)
			print("Completed Batch", currentCount)
			if currentCount % 10 == 0:
				writeFile.close()
				writeFile = open(fileName + str(int(currentCount/10)) + fileType, 'w+')
				print(fileName + str(int(currentCount/10)) + fileType)
	writeFile.close()
	print("Finished writing")

def getComments(id, soup):
	"""Returns the list of comments for 'what was valuable' or 'what could be improved'"""
	try:		
		valuable = soup.find("ul", {"id": id}).text.split("\r\n")
		realValuable = []
		for comment in valuable:
			comment = comment.lstrip()
			if not len(comment) == 0:
				realValuable += [comment]

		return realValuable
	except (AttributeError, UnicodeDecodeError, UnicodeEncodeError):
		return []

def getNum(line):
	""""Returns the subset of characters at the beginning of the string that makes an int"""
	try:
		return int(line[0:3])
	except:
		try:
			return int(line[0:2])
		except:
			return int(line[0])

def getScriptData(script, regex, length):
	""""Returns script data for one of a few specified items"""
	item = []
	try:
		for line in script.split('\n'):
			newLine = re.compile(regex).split(line)
			if len(newLine) > 1:
				item.append(getNum(newLine[1]))
	except:
		item = [0] * length
	return item

#code: 			Department & Number
#semester		Semester
#year 			Year
#courseType		LEC/LAB/SEM...
#professors		String array of professor names
#courseName		String course name
#studentNum		int enrolled students
#avgGrade		float average grade
#gradesVector	int array of earned grades (A, A-, ..., P, NC, I, W)
#valuableComm	string array of 'what was valuable' comments
#improvedComm	string array of 'what could be improved' comments
#attendance		int array of reported attendance stats
#studying		int array of reported studying stats
#reviewGrade	int array of student ratings of the course (A, B, ..., F)
#studyHours		int array of student reports of avg hours studying per week (0-3, 4-6, 7-9, 10+)
#attendanceArr	int array of student reports of course attendance(Always, Most, Half Attendance, Infrequently, Only Exams)
#effectiveTeaching			int array of student reports that professor was effective in teaching the subject matter (Strong Agree, Agree, Neutral, Disagree, Strongly Disagree)
#reasonableExpectations		int array of student reports that professor had reasonable expectations (Strong Agree, Agree, Neutral, Disagree, Strongly Disagree)
def parseFile(fileName):
	"""Given an HTML file name, returns a dictionary containing all the relevant course information"""
	course = {
		"avgGrade": -1,
		"gradesVector": [0] * 15,
		"attendance": [0] * 3,
		"studying": [0] * 3,
		"reviewGrade": [0] * 5,
		"studyHours": [0] * 4,
		"attendanceArr": [0] * 5,
		"effectiveTeaching": [],
		"reasonableExpectations": []
	}
	#Create BS
	with open(fileName, 'rb') as file:
		soup = BeautifulSoup(file, 'html.parser')

	#Parse title
	maybeTitle = soup.findAll("h1", {"class": "centered animated fadeInDown white"})[0].text.split('\n')
	titlePieces = []
	for title in maybeTitle:
		title = title.strip()
		if len(title) > 0:
			titlePieces += [title]

	course.update({'code': titlePieces[0][0:6]})
	semesterAndYear = titlePieces[1].split(' ')
	course.update({'semester': semesterAndYear[0]})
	course.update({'year': semesterAndYear[1]})
	course.update({'courseType': titlePieces[2]})

	#Additionally split by ' and ' & ', '
	professors = soup.find("div", {"class": "col-sx-12 col-sm-12 col-md-12"}).findChildren('h3')[0].text
	course.update({'professors': re.compile("(?: and )|(?:, )").split(professors)})

	course.update({'courseName': soup.find("div", {"class": "col-sx-12 col-sm-12 col-md-12"}).findChildren('h2')[0].text})

	scriptTag = soup.findAll('script')[7].text.split('\n')
	totalUsers = 0
	gradesToGPA = [4.0, 3.7, 3.3, 3.0, 2.7, 2.3, 2.0, 1.7, 1.3, 1.0, 0]
	totalGPAUsers = 0
	avgGrade = 0
	gradesVector = []
	#for weird cases
	rangeVal = 20
	#Relevant script lines, always
	if scriptTag[4].replace(r'\s', '') == '\r':
		rangeVal = 16
	for i in range(rangeVal, rangeVal + 15):
		numberGiven = int(scriptTag[i].split(',')[1])
		gradesVector += [numberGiven]
		if i < rangeVal + 11:
			avgGrade += gradesToGPA[i-rangeVal] * numberGiven
			totalGPAUsers += numberGiven
		totalUsers += numberGiven

	course.update({"studentNum": totalUsers})
	
	#Should only execute if people were in the course
	if not totalUsers == 0:
		course['gradesVector'] = gradesVector

	if not totalGPAUsers == 0:
		course['avgGrade'] = avgGrade / totalGPAUsers

	#Handle comments
	course.update({'valuableComm': getComments("paginate-1", soup)})
	course.update({'improvedComm': getComments("paginate-2", soup)})

	miscMetrics = soup.findAll('div', {'class': 'col-sm-12 col-lg-6'})
	if len(miscMetrics) > 0:
		studying = miscMetrics[0].text.split('\n')
		attendance = miscMetrics[1].text.split('\n')
		course['attendance'] = [float(attendance[3]), float(attendance[5]), float(attendance[7])]
		course['studying'] = [float(studying[3]), float(studying[5]), float(studying[7])]


	scriptData = str(soup.findAll('script')[8]).split("google.visualization.arrayToDataTable([")

	#Not enough review data
	if len(scriptData) > 1:
		course['reviewGrade'] = getScriptData(scriptData[1], '\[\'[A-F]\', ', 5)
		course['studyHours'] = getScriptData(scriptData[2], '\[\'[0-9-+]{3}\', ', 4)
		course['attendanceArr'] = getScriptData(scriptData[3], '\[\'[A-z ]{3,15}\', ', 5)
	

	useScript = 11
	if len(soup.findAll('script')) < 12:
		useScript = 9
	#Not enough review data
	if len(soup.findAll('script')) > 9:
		for line in str(soup.findAll('script')[useScript]).split('\n'):
			newLine = re.compile('\[\'[A-z ]{5,17}\', ').split(line)
			if len(newLine) > 1:
				final = newLine[1].split(', ')
				course['effectiveTeaching'].append(getNum(final[0]))
				course['reasonableExpectations'].append(getNum(final[1]))
	if course['effectiveTeaching'] == []:
		course['effectiveTeaching'] = [0] * 5
		course['reasonableExpectations'] = [0] * 5
	return course


if __name__ == '__main__':
	main()