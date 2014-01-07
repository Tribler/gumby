load_annotations <- function(){
	if(file.exists("annotations.txt")){
		df2 <- read.table("annotations.txt", header = TRUE, check.names = FALSE)
		show_mean <- length(colnames(df2)) != 3
		df2 <- melt(df2)
		df2 <- ddply(df2, .(annotation), summarise, meanx = mean(value), minx = min(value), maxx = max(value))
		df2$linesize <- max((df2$maxx - df2$minx) / 2, 1)
		df2$linepos <- df2$minx + df2$linesize
		return(df2)
	}
}

add_annotations <- function(p, df2){
	if(file.exists("annotations.txt")){
		p <- p + stat_vline(alpha = 0.2, data=df2, xintercept = df2$linepos, size = df2$linesize, mapping = aes(colour=annotation))
		if (show_mean) {
			p <- p + stat_vline(alpha = 0.6, data=df2, xintercept = df2$meanx, size = 1, mapping = aes(colour=annotation))
		}
		p <- p + geom_text(alpha = 0.4, data=df2, angle = 90, aes(x=maxx, y=max(df$value), label=annotation, hjust=1, size=6))
		return(p)
	}
}