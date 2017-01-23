library(ggplot2)
library(reshape)

args <- commandArgs(TRUE)
minX <- as.integer(args[1])
maxX <- as.integer(args[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df3 <- load_annotations()

if(file.exists("fd_usage.log")){
	df <- read.table("fd_usage.log", header = TRUE, check.names = FALSE, na.strings = "?")
	num_columns <- ncol(df) - 1
	df$type <- 'Process'
	df$time <- df$time - df$time[1]

	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df3)
	p <- p + geom_line(alpha=0.8, aes(x=time, y=num_fds, group=pid, colour=pid))
	p <- p + facet_grid(type ~ ., scales = "free_y")
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Number of open file descriptors\n")
	if(length(args) > 0){
		p <- p + xlim(minX, maxX)
	}
	p

	ggsave(file="fd_usage.png", width=12, height=6, dpi=100)
}
