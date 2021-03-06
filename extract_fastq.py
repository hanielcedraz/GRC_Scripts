#!/usr/bin/env python

'''
Extract reads from a SAM or SAM.gz file.

Note (the & operation produces a value equivalent to the binary with a 1 in that position):
0x1 template having multiple segments in sequencing
0x2 each segment properly aligned according to the aligner
0x4 segment unmapped
0x8 next segment in the template unmapped
0x10 SEQ being reverse complemented
0x20 SEQ of the next segment in the template being reversed
0x40 the first segment in the template
0x80 the last segment in the template
0x100 secondary alignment
0x200 not passing quality controls
0x400 PCR or optical duplicate

Note:
  It is necessary to double check that both pairs of the PE read really exist in the SAM
file just in case it somehow gets disordered. This is taken care of by keeping the PE
reads in a set of dictionaries and then deleting them once the pair is written.
In the case where a read is somehow labeled as paired, but the pair doesn't exist, the
read is NOT written.
'''

import sys
import os
from optparse import OptionParser  # http://docs.python.org/library/optparse.html
import gzip


usage = "usage: %prog [options] -o output_base inputfile.SAM"
parser = OptionParser(usage=usage)
parser.add_option('-u', '--uncompressed', help="leave output files uncompressed",
                  action="store_true", dest="uncompressed")
parser.add_option('-o', '--output_base', help="output file basename",
                  action="store", type="str", dest="output_base",default="extracted")
parser.add_option('-v', '--verbose', help="verbose output",
                  action="store_false", dest="verbose", default=True)

(options,  args) = parser.parse_args()  # uncomment this line for command line support


if len(args) == 1:
    infile = args[0]
        #Start opening input/output files:
    if not os.path.exists(infile):
        print "Error, can't find input file %s" % infile
        sys.exit()

    if infile.split(".")[-1] == "gz":
        insam = gzip.open(infile, 'rb')
    else:
        insam = open(infile, 'r')
else:
    ## reading from stdin
    insam = sys.stdin

base = options.output_base


PE1 = {}
PE2 = {}

if options.uncompressed:
    outPE1 = open(base + "_PE1.fastq", 'w')
    outPE2 = open(base + "_PE2.fastq", 'w')
    outSE = open(base + "_SE.fastq", 'w')
else:
    outPE1 = gzip.open(base + "_PE1.fastq.gz", 'wb')
    outPE2 = gzip.open(base + "_PE2.fastq.gz", 'wb')
    outSE = gzip.open(base + "_SE.fastq.gz", 'wb')



def reverseComplement(s):
    """
    given a seqeucne with 'A', 'C', 'T', and 'G' return the reverse complement
    """
    basecomplement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A', 'N': 'N'}
    letters = list(s)
    try:
        letters = [basecomplement[base] for base in letters]
    except:
        raise
    return ''.join(letters[::-1])


def reverse(s):
    """
    given a sequence return the reverse 
    """
    letters = list(s)
    return ''.join(letters[::-1])


def writeread(ID, r1, r2):
    #read1
    outPE1.write("@" + ID + "#0/1" '\n')
    outPE1.write(r1[0] + '\n')
    outPE1.write('+\n' + r1[1] + '\n')
    #read2
    outPE2.write("@" + ID + "#0/2" '\n')
    outPE2.write(r2[0] + '\n')
    outPE2.write('+\n' + r2[1] + '\n')

i = 0
PE_written = 0
SE_written = 0
for line in insam:
    if i % 100000 == 0 and i > 0 and options.verbose:
        print "Records processed: %s, PE_written: %s, SE_written: %s" % (i, PE_written, SE_written)
    #Comment/header lines start with @
    if line[0] != "@" and len(line.strip().split()) > 2:
        i += 1
        line2 = line.strip().split()
        flag = int(line2[1])
        #Handle SE:
        if (flag & 0x100): # secondary alignment
            continue
        # mapped SE reads have 0x1 set to 0, and 0x4 (third bit) set to 1
        if not (flag & 0x1):
            ID = line2[0].split("#")[0]
            if (flag & 0x10):
                line2[9] = reverseComplement(line2[9])
                line2[10] = reverse(line2[10])
            outSE.write("@" + ID + '\n')
            outSE.write(line2[9] + '\n')
            outSE.write('+\n' + line2[10] + '\n')
            SE_written += 1
            continue
        #Handle PE:
        #logic:  0x1 = multiple segments in sequencing,   0x4 = segment unmapped,  0x8 = next segment unmapped
        if (flag & 0x1):
            if (flag & 0x40):  # is this PE1 (first segment in template)
                #PE1 read, check that PE2 is in dict and write out
                ID = line2[0].split("#")[0]
                if (flag & 0x10):
                    line2[9] = reverseComplement(line2[9])
                    line2[10] = reverse(line2[10])
                r1 = [line2[9], line2[10]]  # sequence + qual
                if ID in PE2:
                    writeread(ID, r1, PE2[ID])
                    del PE2[ID]
                    PE_written += 1
                else:
                    PE1[ID] = r1
            elif (flag & 0x80):  # is this PE2 (last segment in template)
                #PE2 read, check that PE1 is in dict and write out
                ID = line2[0].split("#")[0]
                if (flag & 0x10):
                    line2[9] = reverseComplement(line2[9])
                    line2[10] = reverse(line2[10])
                r2 = [line2[9], line2[10]]
                if ID in PE1:
                    writeread(ID, PE1[ID], r2)
                    del PE1[ID]
                    PE_written += 1
                else:
                    PE2[ID] = r2

print "Records processed: %s, PE_written: %s, SE_written: %s" % (i, PE_written, SE_written)

outPE1.close()
outPE2.close()
outSE.close()
