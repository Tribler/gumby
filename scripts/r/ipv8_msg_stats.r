library(ggplot2)
library(reshape)
library(stringr)
library(igraph)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df2 <- load_annotations()

if(file.exists("ipv8_msg_stats.csv")){
	df <- read.csv("ipv8_msg_stats.csv", sep=",", header=T)
    df$msg_id <- as.factor(df$msg_id)

    # Messages sent
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df2)
	p <- p + geom_line(aes(time, num_up, group=msg_id, colour=msg_id))
	p <- p + theme(legend.position="bottom", legend.direction="horizontal")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Total messages sent\n")
	p <- p + xlim(minX, maxX)
	p

	ggsave(file="ipv8_msg_stats_num_up.png", width=8, height=6, dpi=100)

    # Messages received
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df2)
	p <- p + geom_line(aes(time, num_down, group=msg_id, colour=msg_id))
	p <- p + theme(legend.position="bottom", legend.direction="horizontal")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Total messages received\n")
	p <- p + xlim(minX, maxX)
	p

	ggsave(file="ipv8_msg_stats_num_down.png", width=8, height=6, dpi=100)

    # Bytes sent
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df2)
	p <- p + geom_line(aes(time, bytes_up, group=msg_id, colour=msg_id))
	p <- p + theme(legend.position="bottom", legend.direction="horizontal")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Total bytes sent\n")
	p <- p + xlim(minX, maxX)
	p

	ggsave(file="ipv8_msg_stats_bytes_up.png", width=8, height=6, dpi=100)

    # Bytes down
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df2)
	p <- p + geom_line(aes(time, bytes_down, group=msg_id, colour=msg_id))
	p <- p + theme(legend.position="bottom", legend.direction="horizontal")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Total bytes received\n")
	p <- p + xlim(minX, maxX)
	p

	ggsave(file="ipv8_msg_stats_bytes_down.png", width=8, height=6, dpi=100)
}
