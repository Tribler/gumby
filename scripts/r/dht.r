library(ggplot2)
library(reshape)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df3 <- load_annotations()

if(file.exists("dht_response_times.csv")){
	df <- read.table("dht_response_times.csv", header = TRUE, na.strings = "-1")
	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df3)
	p <- p + geom_point(alpha = 0.8, aes(time, response_time, group=peer, colour=factor(peer)))
	p <- p + facet_grid(operation ~ ., scales = "free_y")
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (seconds)", y = "Response time (seconds)\n")
        #p <- p + xlim(minX, maxX)
	ggsave(file="dht_response_times.png", width=8, height=6, dpi=100)
}

