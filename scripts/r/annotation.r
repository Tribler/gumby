library(plyr)
load_annotations <- function(){
	if(file.exists("annotations.txt")){
		df2 <- read.table("annotations.txt", header = TRUE, check.names = FALSE, na.strings = "?")
		show_mean <- length(colnames(df2)) != 3
		df2 <- melt(df2)
		df2 <- na.omit(df2)
		df2 <- ddply(df2, .(annotation), summarise, meanx = mean(value), minx = min(value), maxx = max(value))
		df2$show_mean <- show_mean

		if(length(args) > 0){
			df2$labelpos <- df2$minx + max((maxX - minX) / 66, 1)
		} else {
			df2$labelpos <- df2$minx + 1
		}

		return(df2)
	}
}

add_annotations <- function(p, df, df2){
	if(file.exists("annotations.txt")){
		p <- p + geom_rect(alpha = 0.2, data=df2, aes(xmin=minx, xmax=maxx, ymin=-Inf, ymax=Inf, fill=annotation), show_guide = FALSE)
		for (i in 1:nrow(df2)){
			if (df2$show_mean[i]) {
				p <- p + geom_vline(alpha = 0.6, data=df2, xintercept = df2$meanx[i], size = 1, colour = toString(i+1))
			}
		}
		df3 <- df2[]

		if ('Node' %in% df$type){
			df3$type <- 'Node'
		} else {
			df3$type <- 'Process'
		}
		p <- p + geom_text(alpha = 0.4, data=df3, angle = 90, aes(x=labelpos, y=max(df$value), label=annotation, hjust=1, size=6), show_guide = FALSE)
	}
	return(p)
}

mean_max_min <- function(num_columns, df){
	if (num_columns > 1000){
		tdf <- cbind(df['time'], t(apply(df[,2:ncol(df)], 1, function(x) summary(na.omit(x)))))
		colnames(tdf) <- c('time', 'min', 'Q1', 'median', 'mean','Q3', 'max')
		return(tdf)
	} else {
		tdf <- melt(df, id="time")
		tdf <- na.omit(tdf)
		return(tdf)
	}
}
