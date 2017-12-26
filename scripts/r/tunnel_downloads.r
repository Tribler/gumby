library(ggplot2)
library(reshape)
library(stringr)
library(igraph)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()

if(file.exists("downloads_history.csv")){
	df <- read.csv("downloads_history.csv", sep=",")
	df$total_up = df$total_up / 1024 / 1024
	df$total_down = df$total_down / 1024 / 1024
	df$speed_up = df$speed_up / 1024
	df$speed_down = df$speed_down / 1024
	df$peer = as.character(df$peer)

	for(infohash in unique(df$infohash)) {
		# Total uploaded graph
		p <- ggplot(df) + theme_bw()
		p <- add_annotations(p, df, df2)
		p <- p + geom_line(aes(x=time, y=total_up, group=peer, colour=peer))
		p <- p + theme(legend.position="bottom", legend.direction="horizontal")
		p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Total uploaded (MB)")
		p <- p + xlim(minX, maxX)
		p

		ggsave(file=paste(infohash, "total_up.png", sep="_"), width=8, height=6, dpi=100)

		# Total downloaded graph
		p <- ggplot(df) + theme_bw()
		p <- add_annotations(p, df, df2)
		p <- p + geom_line(aes(x=time, y=total_down, group=peer, colour=peer))
		p <- p + theme(legend.position="bottom", legend.direction="horizontal")
		p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Total downloaded (MB)")
		p <- p + xlim(minX, maxX)
		p

		ggsave(file=paste(infohash, "total_down.png", sep="_"), width=8, height=6, dpi=100)

		# Upload speed graph
		p <- ggplot(df) + theme_bw()
		p <- add_annotations(p, df, df2)
		p <- p + geom_line(aes(x=time, y=speed_up, group=peer, colour=peer))
		p <- p + theme(legend.position="bottom", legend.direction="horizontal")
		p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Upload speed (KB/s)")
		p <- p + xlim(minX, maxX)
		p

		ggsave(file=paste(infohash, "speed_up.png", sep="_"), width=8, height=6, dpi=100)

		# Download speed graph
		p <- ggplot(df) + theme_bw()
		p <- add_annotations(p, df, df2)
		p <- p + geom_line(aes(x=time, y=speed_down, group=peer, colour=peer))
		p <- p + theme(legend.position="bottom", legend.direction="horizontal")
		p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Download speed (KB/s)")
		p <- p + xlim(minX, maxX)
		p

		ggsave(file=paste(infohash, "speed_down.png", sep="_"), width=8, height=6, dpi=100)
	}
}
