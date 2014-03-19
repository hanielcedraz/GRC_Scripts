#!/usr/bin/env python

#Last Modified March 19, 2014 -- Sam Hunter

"""
A pipeline for processing MiSeq runs.
Inputs:
    RunInfo.xml
    SampleSheet.csv
outputs:
    out_dir/run_casava.sh
    out_dir/SampleSheet.csv   <---- Note that this is re-formatted to support CASAVA

Examples (from MiSeq SampleSheet):
No Index:
    [Data]
    Sample_ID,Sample_Name,Sample_Plate,Sample_Well,Sample_Project,Description
    1,1BAT,a,a1,20140315_Kate_Bat_RAD,20140315_Kate_Bat_RAD

Single Index:
[Data]
Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,Sample_Project,Description
A1,A1,,,A001,ATCACG,Description,20140314_Virginia Stockwell02repeat03

Dual Index:
    [Data]
    Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,I5_Index_ID,index2,Sample_Project,Description
    MariyaAmy002,MariyaAmy002,,,D701,ATTACTCG,D501,TATAGCCT,MariyaAmy002,MariyaAmy002

"""
#from Bio import SeqIO
#import gzip
import os
import sys
#import re

#First, get command line arguments:
if len(sys.argv) < 3:
    print "Error, could not find input parameters"
    print "Usage:"
    print "\tmiseq_pipeline.py inputdir outputdir"
    sys.exit()

in_dir = os.path.realpath(sys.argv[1])
out_dir = os.path.realpath(sys.argv[2])

#Check that these are real paths:
if not os.path.exists(in_dir):
    print "Error, could not find input path %s\nExiting...." % in_dir
    sys.exit()
if not os.path.exists(out_dir):
    os.makedirs(out_dir)
    if not os.path.exists(out_dir):
        print "Error, could create output directory: %s\nExiting...." % out_dir
        sys.exit()
else:
    print "Error, output directory %s already exists, please remove it manually" % out_dir
    sys.exit()
if in_dir == out_dir:
    print "Error, input path matches output path.\nExiting...."
    sys.exit()

#Setup run info
runinfo = {}
runinfo['Investigator_Name'] = ""
runinfo['Project_Name'] = ""
runinfo['Experiment_Name'] = ""
runinfo['Date'] = ""
runinfo['Workflow'] = ""
runinfo['Application'] = ""
runinfo['Assay'] = ""
runinfo['Description'] = ""
runinfo['Chemistry'] = ""
runinfo['Flowcell'] = ""
runinfo['reads'] = {}

#Setup samples
samples = []
numfields = 0


### First, process RunInfo.xml for Flowcell:  ###
infn = os.path.join(in_dir, "RunInfo.xml")
if os.path.isfile(infn):
    inf1 = open(infn, 'r')
else:
    print("Error cannot find %s" % infn)
    sys.exit()

for l in inf1:
    l = l.strip()
    if l[0:10] == "<Flowcell>":
        runinfo['Flowcell'] = l[10: l.find("</Flowcell>")]
    if l[0:6] == "<Read ":
        l = l.split("=")
        NumCycles = l[1].split()[0].strip('"')
        Number = int(l[2].split()[0].strip('"'))
        Index = "Y" if l[3].split()[0].strip('"') == 'N' else 'I'
        runinfo['reads'][Number] = Index+NumCycles

inf1.close()

#### Second, process the SampleSheet.csv  ##########
section = ""
fields_idx = {}

infn = os.path.join(in_dir, "SampleSheet.csv")
if os.path.isfile(infn):
    inf1 = open(infn, 'r')
else:
    print("Error cannot find %s" % infn)
    sys.exit()

for l in inf1:
    l = l.strip()
    if l == "[Header]":
        section = "Header"
        continue
    if l == "[Reads]":
        section = "Reads"
        continue
    if l == "[Settings]":
        section = "Settings"
        continue
    if l == "[Data]":
        section = "Data"
        continue
    #This isn't a section delimiter so:
    l = l.split(',')
    ## Store header information:
    if section == "Header":
        for k in runinfo.keys():
            if l[0].replace(" ", "_") == k:
                runinfo[k] = l[1]
    if section == "Data" and l[0] == "Sample_ID":
        numfields = len(l)
        for i, value in enumerate(l):
            fields_idx[value] = i
    if section == "Data" and l[0] != "Sample_ID" and len(l) > 1:
        samples.append(l)
inf1.close()

## Input files are both loaded, now generate output:

# Build SampleSheet.csv
print "Building SampleSheet.csv....."
outfn = os.path.join(out_dir, "SampleSheet.csv")
outf1 = open(outfn, 'w')
outf1.write("ID,Lane,SampleID,SampleRef,Index,Description,Control,Recipe,Operator,SampleProject\n")
for s in samples:
    ID = runinfo['Flowcell']
    Lane = str(1)
    # Set up all of the columns:
    SampleID = SampleRef = Index = Description = ""
    #SampleID = s[1]
    if 'SampleID' in fields_idx:
        SampleID = s[fields_idx['SampleID']]
    #SampleRef = s[3]
    if 'SampleRef' in fields_idx:
        SampleRef = s[fields_idx['SampleRef']]
    if 'Description' in fields_idx:
        Description = s[fields_idx['Description']]
    if 'index' in fields_idx:
        Index = s[fields_idx['index']]
    if SampleID == "":
        SampleID = s[0]
    # dual barcode samples are handled specially, we want 4 reads instead of a split set.
    if numfields == 10:
        #Index = s[5] + "-" + s[7]
        #Description = s[9]
        Index = ""
        runinfo['reads'][2] = runinfo['reads'][2].replace("I", "Y")
        runinfo['reads'][3] = runinfo['reads'][3].replace("I", "Y")
    # if numfields == 9:
    #     #Index = s[5]
    #     Index = s[fields_idx['']]
    #     #Description = s[7]
    # if numfields == 8:
    #     Index = s[5]
    #     #Description = s[7]
    # if numfields == 6:
    #     Index = s[3]
    #     #Description = s[5]
    txt = ",".join([ID, Lane, SampleID, SampleRef, Index, Description, "N", "", "tech", runinfo["Project_Name"]])
    outf1.write(txt + '\n')
outf1.close()

# Build run_casava.sh:
print "Building run_casava.sh...."
outfn = os.path.join(out_dir, "setup_casava.sh")
outf1 = open(outfn, 'w')
txt = "/mnt/home/msettles/opt/CASAVA/bin/configureBclToFastq.pl"
txt += " --input-dir %s --output-dir %s --sample-sheet %s --mismatches 1 --fastq-cluster-count 0" % (os.path.join(in_dir, "Data/Intensities/BaseCalls"), os.path.join(out_dir, "Split"), os.path.join(out_dir, "SampleSheet.csv"))
txt += " --use-bases-mask "
txt += ",".join(map(lambda i: runinfo['reads'][i], range(1, len(runinfo['reads']) + 1)))
txt += "\n"

outf1.write(txt)
# if I need to write read info (this is in the xml, and it appears that CASAVA grabs it but...)
outf1.close()


print "All processing complete, %s total samples found" % len(samples)
