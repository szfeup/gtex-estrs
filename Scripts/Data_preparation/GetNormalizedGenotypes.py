	#Corrected
import argparse
import math
import numpy as np
import sys
import vcf

SAMPLES = []
VCFFILE = ""
OUTFILE = ""
MINMAF = 0.0
GTFIELD = "GT"
MINSAMPLES = 50
MINCOUNT = 1
NORM = True
COUNTFILTERS = False
DEBUG = False
FILTER = False

def GetGT(gt):
    #print gt
    if gt is None: return None
    if str(gt) == "." or str(gt) == "./.": return None #Missing genotype control
    if "|" in gt: return map(int, gt.split("|"))
    elif "/" in gt: return map(int, gt.split("/"))
    else: return [int(gt), int(gt)] # haploid

def SetNone(item, setnull):
    if item == setnull: return None
    else: return item

def PruneRareGT(gtsum, MINCOUNT):
    """
    For genotypes that occur less than MINCOUNT times, set those to None
    """
    gts = set([item for item in gtsum if item is not None])
    for gt in gts:
        if gtsum.count(gt) < MINCOUNT:
            gtsum = map(lambda x: SetNone(x, gt), gtsum)
    return gtsum

def checkgt(record,s):
    try:
        return(record.genotype(s)[GTFIELD])
    except:
        return None
    
def NormalizeGT(genotypes, NORM=True, PRINT_ALLELES=False, MINCOUNT=1, COUNTFILTERS=False):
    def getsum(x):
        if x is None: return None
        else: return sum(x)
    def getstr(x):
        if x is None: return "NA,NA"
        else: return ",".join(map(str, x))
    if PRINT_ALLELES: return map(getstr, genotypes)
    gtsum = map(getsum, genotypes)
    if MINCOUNT > 1:
        gtsum = PruneRareGT(gtsum, MINCOUNT)
    if len(set([item for item in gtsum if item is not None])) == 1:
        return None # no variation
    if COUNTFILTERS:
        return gtsum # just counting filters, don't waste time to actually normalize
    if not NORM: return gtsum
    gtmean = np.mean([item for item in gtsum if item is not None])
    gtsd = math.sqrt(np.var([item for item in gtsum if item is not None]))
    if gtsd == 0: return None
    def norm(gt, m, s):
        if gt is None: return None
        else: return (gt-m)*1.0/s
    gtnorm = [norm(item, gtmean, gtsd) for item in gtsum]
    return gtnorm

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get normalized genotypes")
    parser.add_argument("--samples", help="File containing list of samples to include (default: all)", type=str)
    parser.add_argument("--vcf", help="VCF file with genotypes", type=str, required=True)
    parser.add_argument("--out", help="Output file", type=str)
    parser.add_argument("--minmaf", help="Only include SNPs with at least this MAF in EUR (default: 0.0). If in INFO field, use that. Else calculate the MAF", type=float)
    parser.add_argument("--gtfield", help="Which field to get genotypes from. Default: GT", type=str)
    parser.add_argument("--minsamples", help="Require genotypes in at least this many samples. Default: 50", type=int)
    parser.add_argument("--nonorm", help="Don't normalize genotypes, just return raw genotypes in a matrix.", action="store_true")
    parser.add_argument("--mincount", help="Don't return genotypes with less than this many occurrences", type=int)
    parser.add_argument("--alleles", help="Print allele1, allele2 rather than sum of alleles", action="store_true")
    parser.add_argument("--filter", help="Only consider records that passed filters. FILTER is PASS", action="store_true")             ######    
    parser.add_argument("--countfilters", help="Just print out the number of loci filtered by each criteria", action="store_true")
    parser.add_argument("--debug", help="Print debug info", action="store_true")
    args = parser.parse_args()

    if args.out is None and not args.countfilters:
        sys.stderr.write("ERROR: Must specify --out\n")
        sys.exit(1)
    if args.samples:
        SAMPLES = map(lambda x: x.strip(), open(args.samples, "r").readlines())
    if args.minmaf is not None:
        MINMAF = args.minmaf
    if args.gtfield is not None:
        GTFIELD = args.gtfield
    if args.minsamples is not None:
        MINSAMPLES = args.minsamples
    if args.mincount is not None:
        MINCOUNT = args.mincount
    if args.nonorm: NORM=False
    DEBUG = args.debug
    PRINT_ALLELES = args.alleles
    COUNTFILTERS = args.countfilters
    if args.filter: FILTER=True             ######

    VCFFILE = args.vcf
    OUTFILE = args.out
    vcf_reader = vcf.Reader(open(VCFFILE, "rb"))
    if SAMPLES == []: SAMPLES = vcf_reader.samples
    SAMPLES = [item for item in SAMPLES if item in vcf_reader.samples]

    counters = {
        "numloci": 0,
        "minmaf": 0,
        "minsamples": 0,
        "novar": 0,
        "keepers": 0
        }

    if not COUNTFILTERS:
        out = open(OUTFILE, "w")
        out.write("\t".join(["chrom","start"] + SAMPLES)+"\n")
        
        
    for record in vcf_reader:
        if (FILTER==True) and (record.FILTER != []):         # Filter variants that passed filters in vcf 
            continue
        else:
            print record.ID, '   ', record.FILTER, '   ', record.QUAL
            if record.call_rate == 0:       # otherwise pyvcf functions break
                counters["minsamples"] = counters["minsamples"] + 1
                continue
            counters["numloci"] = counters["numloci"] + 1
            maf = min([max(record.aaf), 1-max(record.aaf)])
            if maf < MINMAF:
                counters["minmaf"] = counters["minmaf"] + 1
                continue
            chrom = record.CHROM
            if "chr" not in chrom: chrom = "chr%s"%chrom
            pos = record.POS            
            genotypes = [GetGT(checkgt(record,s)) for s in SAMPLES]
            print record.ID, ' ', len(genotypes), ' ', record.FORMAT  ###
            if len([item for item in genotypes if item is not None]) < MINSAMPLES:
                counters["minsamples"] = counters["minsamples"] + 1
                continue
    #	print MINCOUNT, '\n', genotypes
            genotypes_norm = NormalizeGT(genotypes, NORM=NORM, PRINT_ALLELES=PRINT_ALLELES, MINCOUNT=MINCOUNT, COUNTFILTERS=COUNTFILTERS)
            if genotypes_norm is None:
                counters["novar"] = counters["novar"] + 1
                if DEBUG: sys.stderr.write("Discarding %s:%s, no variation after processing\n"%(chrom, pos))
            else:
                if not COUNTFILTERS: out.write("\t".join(map(str,[chrom,pos]+genotypes_norm))+"\n")
                counters["keepers"] = counters["keepers"] + 1
            if counters["numloci"]%100 == 0: sys.stderr.write("%s\n"%counters)
            if DEBUG and counters["numloci"]>100: break
    if not COUNTFILTERS:
        out.close()

#   print counter info
    sys.stdout.write("Total number of loci: %s\n"%counters["numloci"])
    sys.stdout.write("Filtered for MAF: %s\n"%counters["minmaf"])
    sys.stdout.write("Filtered for num samples: %s\n"%counters["minsamples"])
    sys.stdout.write("Filtered for no variation: %s\n"%counters["novar"])
    sys.stdout.write("Keepers: %s\n"%counters["keepers"])
