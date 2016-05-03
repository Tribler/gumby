library(ggplot2)
library(foreach)
library(data.table)

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df3 <- load_annotations()

logfilename <- "network_usage.log"

if(file.exists(logfilename)){
	dataframe <- read.table(logfilename, header = FALSE, check.names = FALSE, na.strings = "?")
	colnames(dataframe) <- c("timestamp", "device", "receivedbytes", "receivedpackets", "receivederrs", "receiveddrop", "receivedfifo", "receivedframe", "receivedcompressed", "receivedmulticast", "transmitbytes", "transmitpackets", "transmiterrs", "transmitdrop", "transmitfifo", "transmitcolls", "transmitcarrier", "transmitcompressed")

	# These statistics will be plotted.
	labelnames <- c("Bytes received", "Bytes transmitted", "Received packets dropped", "Transmitted packets dropped")
	headernames <- c("receivedbytes", "transmitbytes", "receiveddrop", "transmitdrop")

	# For each of these statistics, make a plot.
	foreach(plotiter=1:length(headernames)) %do% {
		statistic <- headernames[plotiter]
		statisticName <- labelnames[plotiter]

		# Split frame per device for easier cleanup.
		splitframe <- split(dataframe, dataframe$device)
		plotframes <- c()

		foreach(i = 1:length(splitframe)) %do% {
			deviceframe <- splitframe[[i]]
			devicename <- deviceframe$device[1]
			deltaColumnName <- paste(statistic, "Delta", sep="")
			
			# Calculate delta (per time unit) by subtracting value of previous row.
			deviceframe[deltaColumnName] <- c(0, deviceframe[2:nrow(deviceframe), statistic] - deviceframe[1:(nrow(deviceframe)-1), statistic])

			# Create 'per second' data for plot.
			deviceframe$timestampint <- floor(deviceframe$timestamp)
			deviceframe <- aggregate(deviceframe[deltaColumnName], deviceframe['timestampint'], sum)
			deviceframe["device"] <- devicename

			# Add cleaned data to list.
			plotframes[[i]] <- deviceframe
		}

		# Concatenate list.
		plotdata <- rbindlist(plotframes)
		# Create extra column for facet.
		plotdata$type <- "device"
		# Create and concatenate aggregate data.
		total <- plotdata[, sum(get(deltaColumnName)), by=list(timestampint)]
		setnames(total, c("timestampint", deltaColumnName))
		total$device = NA
		total$type = "aggregate"
		plotdata <- rbind(plotdata, total)

		# Make timestamp relative to start of experiment.
		plotdata$timestampint <- plotdata$timestampint - plotdata$timestampint[1]

		# Make plot.
		plot <- ggplot(plotdata) + theme_bw()
		plot <- plot + geom_line(alpha = 0.8, aes_string(x="timestampint", y=deltaColumnName, group="device", colour="device"))
		plot <- plot + labs(x = "\nTime into experiment (Seconds)", y = paste(statisticName, "/second\n", sep=""))
		plot <- plot + facet_grid(type ~ .)
		print(plot)

		ggsave(file=paste("network-", statistic, ".png", sep=""), width=12, height=6, dpi=100)
	}
}

