#import ms.version
import os
import time
#ms.version.addpkg("numpy","1.11.0")
#ms.version.addpkg("pytz","2014.10")
#ms.version.addpkg("dateutil","2.5.2")

#args -M : Mappings File
#args -A : Aliases File
#args -F : FileToProcess
#args -D : DataSetName
#args -B : BusinessDate
#args -C : ConfigFile

import argparse
try:
    import configparser as ConfigParser
except ImportError:
    import ConfigParser
import logging

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = '')
    parser.add_argument('-M','--Mappings',help="Mappings File Path", required = True)
    parser.add_argument('-A','--Aliases',help="Aliases File Path",required = True)
    parser.add_argument('-C','--Config',help="Configuration Properties File Path",required = True)
    parser.add_argument('-F','--FileToProcess',help="Input File to Process (In case of Single File)")
    parser.add_argument('-D','--DataSetName',help="DataSetName of File to Process (In case of Single File)",required = True)
    parser.add_argument('-B','--BusinessDate',help="BusinessDate",required = True)
    parser.add_argument('-L','--LoggingLevel',choices=['DEBUG', 'INFO', 'WARNING','ERROR'],help="LoggingLevel",required = True)
    
    # python Reconer_Main.py -M Mappings.txt -A Aliases.txt -F D:\tempDir\Input_Files\mhub_mdw_recon_orig_loan_{YYYYMMDD}.dat -B 20200610 -D Origination_Loan -C config.properties -L INFO
    args = vars(parser.parse_args())
    print("Args are %s",args)
    
mappingFile = args['Mappings']
aliasesFile = args['Aliases']
configFile = args['Config']
fileToProcess = args['FileToProcess']
dataSetName = args['DataSetName']
businessDate = args['BusinessDate']
logLevel = args['LoggingLevel']


def getCustomLogger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logLevel)
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler("diagnostic.log", 'w')
    c_format = logging.Formatter('%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')
    f_format = logging.Formatter('%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)
    return logger

logger = getCustomLogger("Reconer_Main")
logger.info("Args are %s",args)

def getConfigProperty(section_name, key_name):    
    config = ConfigParser.RawConfigParser()
    config.optionxform = str
    config.read(configFile)
    return config.get(section_name, key_name)

mappingOpen = open(mappingFile,'r')
mapperLine = ""
while True:
    line = mappingOpen.readline()
    if not line: 
        break
    strLine = line.strip()
    logger.info(strLine)
    if(dataSetName == strLine.split("|")[1].strip()):
        mapperLine = strLine
        break

def parseFileLink(fileLink, busDate, busDateParam):
    return (fileLink.strip().replace(busDateParam, busDate)) 

fileInfo = mapperLine.split("|")
logger.info("File to Process is %s", fileInfo[0])
inputfileName = ""
if(str(fileInfo[0]).index(getConfigProperty("INPUTS","BUSINESS_DATE_PARAM"))>-1):
    inputfileName = parseFileLink(fileInfo[0], businessDate, getConfigProperty("INPUTS","BUSINESS_DATE_PARAM"))
else:
    inputfileName = fileInfo[0]
logger.info("Actual File to Process is %s",inputfileName)
keyColIndicesText = fileInfo[3].strip()
keyColIndices = keyColIndicesText.split(",")
logger.info("KeyCols from file are %s ",keyColIndices)

outFileType = getConfigProperty("INPUTS", "OUTPUT_FILE_TYPE")
outFileDir = getConfigProperty("INPUTS", "OUTPUT_DIRECTORY")
outFileName = ""

if("SINGLE" == outFileType.strip()):
    outFileName = os.path.join((outFileDir), (parseFileLink(getConfigProperty("INPUTS", "SINGLE_OUTFILE_NAME"), getConfigProperty("INPUTS", "BUSINESS_DATE"), getConfigProperty("INPUTS", "BUSINESS_DATE_PARAM"))))
    # headerOn = True
    logger.debug("Using Ouput File : " + outFileName)
    # CREATE OUTPUTFILE DIRECTORY STRUCTURE IF NOT PRESENT
    if not (os.path.exists(outFileDir)):
        logger.debug("Output Directory Does not Exist : " + outFileDir)
        logger.debug("Creating Output Directory : " + outFileDir)
        os.makedirs(outFileDir)
    # OPEN OUT FILE
    openOutfile = open(outFileName, "w")
    openOutfile.write(getConfigProperty("INPUTS", "OUTPUT_FILE_HEADER") + "\n")
    openOutfile.close()
else:
    path, name = os.path.split(inputfileName)
    outFileNm = getConfigProperty("INPUTS", "OUTPUT_FILE_PREFIX") + "_" + name.strip()
    outFileName = os.path.join(outFileDir, outFileNm)
    
logger.debug("Using Ouput File : " + outFileName)

KeyColumnNameIndices = {}
NonKeyColumnNameIndices = {}

isAlias = True
if('True' == getConfigProperty('INPUTS', 'SET_ALIAS')):
    isAlias = True
else:
    isAlias = False
logger.info("Aliasing is set to %s",isAlias)    


def getAliasesDict(section):
    aliases = {}
    config = ConfigParser.RawConfigParser()
    config.optionxform = str
    config.read(aliasesFile)
    if(config.has_section(section)):
        aliases = config.items(section)
    else:
        logger.info("Aliases for Section : %s are not present in the Aliases File!!",section)
    
    logger.info("Aliases are %s",aliases)
    return aliases

AliasesDict = dict(getAliasesDict(dataSetName))
logger.info("Aliases are %s",AliasesDict)

def frameColumnsIndices(columns,keyColindicesText):
    keyColNI = {}
    nonkeyColNi = {}
    indexArray = keyColindicesText.split(',')
    logger.info("Columsns Text is %s",columns)
    columnsArray = columns.split('|')
    
    
    for val in set(range(0, len(indexArray), 1)):
        logger.info("Preserving Order val is %s, IndexArray[val] is %s and columnsArray[int(indexArray[val])] is %s",val,indexArray[val],columnsArray[int(indexArray[val])])
        keyColNI.setdefault(int(indexArray[val]), columnsArray[int(indexArray[val])])
    logger.info("KeyIndex and Col Names are %s", keyColNI)
    for valu in set(range(0, len(columnsArray), 1)):
        if not valu in list(map(int, keyColNI.keys())):
            nonkeyColNi.setdefault(int(valu), columnsArray[valu])
    logger.info("NonKeyIndex and Col Names are %s", nonkeyColNi)       
    #i=0
    #===========================================================================
    # for val in set(range(0, len(columns), 1)):
    #     logger.debug("Val is %s ",val)
    #     if str(val) in keyColindices:
    #         keyColNI.setdefault(val, columns[val])
    #         #0,COL2
    #     else:
    #         nonkeyColNi.setdefault(val, columns[val])
    # 
    #===========================================================================
    return keyColNI,nonkeyColNi

def frameAliasedColumnNameIndices(keyCols,nonKeyCols,aliasDict):
    a_keyCols = {}
    a_nonkeycols = {}
    logger.debug("keyCols is %s",keyCols)
    logger.debug("nonkeyCols is %s",nonKeyCols)
    logger.debug("aliasdict is %s",aliasDict)
   
    for ind,colName in keyCols.items():
        logger.info("Index is %s and Columnname is %s",ind,colName)
        if colName in aliasDict.keys():
            logger.debug("Colname is %s",colName)
            logger.debug("Aliased Colname is %s",aliasDict.get(colName))
            a_keyCols.setdefault(int(ind), aliasDict.get(colName))
        else:
            a_keyCols.setdefault(int(ind), colName)
    logger.info("AliasedKeyCols are %s",a_keyCols)
    
    for ind,colName in nonKeyCols.items():
        if colName in aliasDict.keys():
            a_nonkeycols.setdefault(int(ind), aliasDict.get(colName))
        else:
            a_nonkeycols.setdefault(int(ind), colName)
    logger.info("AliasedNonKeyCols are %s",a_nonkeycols)
    return a_keyCols,a_nonkeycols

def getColumnValues(dataLine,keyColsdict, nonkeycolsdict):
    keyValDict = {}
    nonkeyValDict = {}
    datas = dataLine.split("|")
    
    for ind in keyColsdict.keys():
        logger.debug("Key Col Index is %s",ind)
        keyValDict.setdefault(keyColsdict.get(ind), datas[ind])
    
    for valu in set(range(0, len(datas), 1)):
        if not valu in list(map(int, keyColsdict.keys())):
            nonkeyValDict.setdefault(nonkeycolsdict.get(valu), datas[valu])
     
    
    
    #===========================================================================
    # for i in list(range(0,len(datas),1)):
    #     logger.info("Val of I is %s and keyCol  Keys are %s",i,list(map(int,keyColsdict.keys())))
    #     if i in list(map(int,keyColsdict.keys())):
    #         logger.info(" %s is present in %s. Adding Maps %s : %s",i,list(map(int,keyColsdict.keys())),keyColsdict.get(i),datas[i])
    #         keyValDict.setdefault(keyColsdict.get((i)),datas[i])
    #     else:
    #         nonkeyValDict.setdefault(nonkeycolsdict.get(i),datas[i])
    #===========================================================================
    logger.debug("KeyColValues is %s",keyValDict)
    logger.debug("NonKeyColValues is %s",nonkeyValDict)
    return keyValDict,nonkeyValDict
            

startTime = time.time()*1000
logger.info("************File Processing Started at %s",time.asctime(time.localtime(time.time())))
openInputFile = open(inputfileName,'r')
openOutFile = open(outFileName,'a')
if not ("SINGLE" == outFileType.strip()):
    openOutFile.write(getConfigProperty("INPUTS", "OUTPUT_FILE_HEADER") + "\n")


AliasedKeyColumnNameIndices = {}
AliasedNonKeyColumnNameIndices = {}   
i = 0
while True:
    i = i + 1
    line = openInputFile.readline()
    strLine = line.strip()
    # print("Line# is ",i," : Line is ",str)
    # BREAK THE LOOP ON END OF FILE
    if not line: 
        break
        
    # SKIPPING HEADER LINE IN FILE
    if strLine.startswith("HDR"):
        continue    
        
    # SKIPPING FOOTER LINE IN FILE
    if strLine.startswith("TRL"):
        continue   
        
    #===========================================================================
    if (i == 2):
            columns = strLine
            logger.debug("Identified Columns In this File are %s",columns.split("|"))
            #KeyColumnNameIndices, NonKeyColumnNameIndices = frameColumnsIndices(columns.split("|"),keyColIndices)
            KeyColumnNameIndices, NonKeyColumnNameIndices = frameColumnsIndices(columns,keyColIndicesText)
            if(isAlias):                
                AliasedKeyColumnNameIndices, AliasedNonKeyColumnNameIndices = frameAliasedColumnNameIndices(KeyColumnNameIndices,NonKeyColumnNameIndices,AliasesDict)
    else:        
        keyColNameValues = {}
        nonKeyColNameValues = {}
        commonOutline = businessDate+"|"+dataSetName
        if not(isAlias):
            keyColNameValues,nonKeyColNameValues = getColumnValues(strLine,KeyColumnNameIndices,NonKeyColumnNameIndices)
            #commonOutline = commonOutline + "|" + str(",".join(KeyColumnNameIndices.values()))+ "|" + str(",".join(KeyColumnNameIndices.values()))
        else:
            keyColNameValues,nonKeyColNameValues = getColumnValues(strLine,AliasedKeyColumnNameIndices,AliasedNonKeyColumnNameIndices)
            #commonOutline = commonOutline + "|" + str(",".join(AliasedKeyColumnNameIndices.values()))
        
        logger.info("KeyColNames and Values is %s",keyColNameValues)   
        logger.info("NonKeyColNames and Values is %s",nonKeyColNameValues)
        FinalCommonOutLine = commonOutline +"|"+str(",".join(keyColNameValues.keys()))+"|"+str(",".join(keyColNameValues.values()))
        logger.info("FinalCommonOutline : %s",FinalCommonOutLine)
        for key,val in nonKeyColNameValues.items():
            if not (key == "record_type"):
                logger.debug("Final Write Line is %s ",(FinalCommonOutLine+"|"+key+"|"+val))
                openOutFile.write((FinalCommonOutLine+"|"+key+"|"+val+"\n").strip('"'))
    #===========================================================================        
openOutFile.close()
openInputFile.close()
endTime = time.time()*1000
logger.info("Time Taken for File Processing : %s secs",(endTime-startTime)/1000)
logger.info("************File Processing Ended at %s",time.asctime(time.localtime(time.time())))

