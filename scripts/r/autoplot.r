if (!require(ggplot2)){
    install.packages('ggplot2', repos="http://cran.us.r-project.org")
}

args <- commandArgs(TRUE)
minX <- as.integer(args[1])
maxX <- as.integer(args[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df3 <- load_annotations()

for (file in list.files(pattern="*.csv", path="autoplot")){
	file_name_no_ext <- tools::file_path_sans_ext(file)

	df <- read.csv(paste("autoplot", file, sep="/"), check.names=FALSE)

	df$type <- 'Process'
	df$time <- df$time - df$time[1]
	variable_name <- tail(names(df), n = 2)[1]

	p <- ggplot(df) + theme_bw()
	p <- add_annotations(p, df, df3)
	p <- p + geom_line(aes(x=time, y=get(variable_name), group=pid, colour=pid, alpha=0.8))
	p <- p + facet_grid(type ~ ., scales = "free_y")
	p <- p + theme(legend.position = "none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = paste(variable_name, "\n", sep=""))
	if(length(args) > 0){
		p <- p + xlim(minX, maxX)
	}
	p

	ggsave(file=paste(file_name_no_ext, ".png", sep=""), width=12, height=6, dpi=100)
}