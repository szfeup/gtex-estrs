#!/bin/bash

source params.sh

BAMS=$(ls /storage/gtex-data/wgs/*.bam | awk '{print $0 ","}' | tr -d '\n' | sed s'/,$//')

HipSTR \
    --bams ${BAMS} \
    --fasta /mnt/resources/Homo_sapiens_assembly19.fasta \
    --regions /mnt/resources/GRCh37.hipstr_reference.bed \
    --min-reads 50 \
    --str-vcf /storage/vcfs/${SAMPLE}.vcf.gz \
    --log /storage/vcfs/${SAMPLE}.log.txt
tabix -p vcf /storage/vcfs/${SAMPLE}.vcf.gz
