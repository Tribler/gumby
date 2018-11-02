library(ggplot2)
library(reshape)

minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

source(paste(Sys.getenv('R_SCRIPTS_PATH'), 'annotation.r', sep='/'))
df3 <- load_annotations()

for (file in list.files(pattern="*.csv", path="autoplot")){
	file_name_no_ext <- tools::file_path_sans_ext(file)

	df <- read.csv(paste("autoplot", file, sep="/"), check.names=FALSE)

	df$type <- 'Process'
	variable_name <- tail(names(df), n = 2)[1]

    pids <- unique(df$pid)
    approximators <- c()
    for (pid in pids) {
        subdf <- df[df$pid == pid, ]
        approximators <- c(approximators, approxfun(subdf$time, subdf[[variable_name]], rule=2))
    }
    agg_df <- data.frame("pid" = pids, "approximator" = NA)
    agg_df$approximator <- approximators

    agg_sum <- function(x) Reduce("+", lapply(approximators, do.call, as.list(c(x))))
    de <- data.frame("time" = df$time)
    de[variable_name] <- unlist(lapply(df$time, agg_sum))
	de$type <- 'Node'
	de$pid <- 0
	df <- rbind(df, de)

	df$value <- df[variable_name]

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