# Set command line args, set defaults so we can run the script from R console as well
args = commandArgs(trailingOnly = TRUE)
if(length(args) > 2) {
  reportName = args[1]
  csvFile = args[2]
  description = args[3]
  outputDir = args[1]
} else {
  reportName = 'test'
  csvFile = '/home/corpaul/workspace/gumbydata/data/Test_performance_Tribler_idle_all_revs_with_guard/output/IdleTribler_1_5_6ccb7518d0ea78248108513065a53efd9125332a.csv'
  description = 'Test run from R console'
  outputDir = "/tmp/perf_reports/"
}



# Read data
csvData = read.csv(csvFile)



# Make summary
rowCount = nrow(csvData)
#totalBytes = sum(as.numeric(as.character(data$BYTES)))
totalBytes = sum(as.numeric(csvData$BYTES))
sink(sprintf("%s/summary.txt", outputDir))

cat(sprintf("Report name: %s\n", reportName))
cat(sprintf("Data monitored for: %s\n", description))
cat(sprintf("Total number of write transactions is: %d\n", rowCount))
cat(sprintf("Total bytes written is: %.0f\n", totalBytes))
sink()

csvData$type = 'other'
csvData$type[grep("etilqs", csvData$FILE)] <- "temp_table"
csvData$type[grep("db-wal", csvData$FILE)] <- "commit"
csvData$type[grep("torrent", csvData$FILE)] <- "torrent"



# get top 20 IO writes per stacktrace
bytescountPerStacktraceTop20 = aggregate(csvData$BYTES, by=list(csvData$TRACE, csvData$type, csvData$PROCESS), FUN=sum)
colnames(bytescountPerStacktraceTop20) <- c("TRACE", "FILE", "PROCESS", "BYTES")

bytescountPerStacktrace = aggregate(csvData$BYTES, by=list(csvData$TRACE), FUN=sum)
colnames(bytescountPerStacktrace) <- c("TRACE", "BYTES")

counts <- aggregate(csvData$BYTES, by=list(csvData$TRACE),FUN="length")
colnames(counts) <- c("TRACE", "count")

bytescountPerStacktrace = merge(bytescountPerStacktrace, counts, by = "TRACE")
colnames(bytescountPerStacktrace) <- c("TRACE", "BYTES", "COUNT")

bytescountPerStacktraceTop20 = merge(bytescountPerStacktraceTop20, counts, by = "TRACE")
colnames(bytescountPerStacktraceTop20) <- c("TRACE", "FILE", "PROCESS", "BYTES", "COUNT")

top20PerStacktrace = bytescountPerStacktraceTop20 [with(bytescountPerStacktraceTop20 , order(-BYTES))[1:30],]
write.csv(top20PerStacktrace, file=sprintf("%s/top20_per_stacktrace.csv", outputDir))

# calculate percentage and write to file for comparison
library(plyr)
perc<-ddply(bytescountPerStacktrace,.(TRACE=TRACE), summarize, PERC = (BYTES/totalBytes)*100)
bytescountPerStacktrace = merge(bytescountPerStacktrace, perc, by = "TRACE")

#totalBytes
sum(bytescountPerStacktrace$PERC)

write.csv(bytescountPerStacktrace, file=sprintf("%s/summary_per_stacktrace.csv", outputDir))

# get top 20 IO writes per filename
bytescountPerFilename = aggregate(csvData$BYTES, by=list(csvData$FILE, csvData$type, csvData$PROCESS), FUN=sum)


colnames(bytescountPerFilename) = c("FILE", "type", "PROCESS", "BYTES")
topsize = min(30, length(bytescountPerFilename$FILE))
top20PerFilename = bytescountPerFilename[with(bytescountPerFilename, order(-BYTES))[1:topsize],]
write.csv(top20PerFilename , file=sprintf("%s/top20_per_filename.csv", outputDir))


# get top 20 IO writes per filename
topLargestWrites = csvData[with(csvData, order(-BYTES))[1:topsize],]
write.csv(topLargestWrites , file=sprintf("%s/top_largest_writes.csv", outputDir))


# graph top 50 writes per filename
#top100PerFilename = bytescountPerFilename[with(bytescountPerFilename, order(-BYTES))[1:50],]


#bytescountPerFilename$type <- factor(bytescountPerFilename$type) # it must be a factor
#bytescountPerFilename$color[bytescountPerFilename$type=='sqlite'] <- "red"
#bytescountPerFilename$color[bytescountPerFilename$type=='torrent'] <- "blue"
#bytescountPerFilename$color[bytescountPerFilename$type=='other'] <- "green"

topPerFilename = bytescountPerFilename[with(bytescountPerFilename, order(-BYTES))[1:topsize],]

library(ggplot2)


# Remove specific paths


#topPerFilename = as.data.frame(sapply(topPerFilename,gsub,pattern="/home/user/Desktop/TriblerDownloads",replacement=""))

#topPerFilename$BYTES = as.numeric(levels(topPerFilename$BYTES)[topPerFilename$BYTES])


minVal = min(topPerFilename$BYTES)
maxVal = max(topPerFilename$BYTES)

# order by bytes
ticksSeq = seq(0, maxVal, by=maxVal/10)

#qplot(x = BYTES, y = FILE, data = topPerFilename, geom = "point", colour=topPerFilename$color, facets = ~ topPerFilename$color )
topPerFilename$FILE <- reorder(topPerFilename$FILE, -topPerFilename$BYTES)


p = ggplot(data = topPerFilename, aes(x = topPerFilename$BYTES, y = topPerFilename$FILE, colour = topPerFilename$type))
p + geom_point() +
 scale_x_continuous(breaks=ticksSeq, limits = c(0,maxVal), expand = c(0,0)) +
 theme(axis.text.x=element_text(angle = 90))
ggsave(file=sprintf("%s/top_per_filename.svg", outputDir), width=18, height=6, dpi=100)



#dotchart(topPerFilename$BYTES,labels=topPerFilename$FILE,cex=.7,groups= topPerFilename$type,
#        main="Bytes written to file\ngrouped by type of write",
#       xlab="Bytes written", gcolor="black", color=topPerFilename$color)
#jpeg(filename = sprintf("python/PerformanceReports/%s/topPerFilename.jpg", reportName))



#timePerStacktrace = aggregate(data$TIME, by=list(data$TRACE, data$FILE, data$PROCESS), FUN=sum)
#top20TimePerStacktrace = timePerStacktrace [with(timePerStacktrace , order(-x))[1:20],]
#colnames(top20TimePerStacktrace) <- c("TRACE", "FILE", "PROCESS", "TIME(us)")
#write.csv(top20TimePerStacktrace, file=sprintf("python/PerformanceReports/%s/Top20TimePerStacktrace.csv", reportName))
