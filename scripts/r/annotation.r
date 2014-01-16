load_annotations <- function(){
	if(file.exists("annotations.txt")){
		df2 <- read.table("annotations.txt", header = TRUE, check.names = FALSE)
		show_mean <- length(colnames(df2)) != 3
		df2 <- melt(df2)
		df2 <- ddply(df2, .(annotation), summarise, meanx = mean(value), minx = min(value), maxx = max(value))
		df2$linesize <- max((df2$maxx - df2$minx) / 2, 1)
		df2$linepos <- df2$minx + df2$linesize
		df2$labelpos <- df2$maxx + max((maxX - minX) / 66, 1)
		df2$show_mean <- show_mean
		return(df2)
	}
}

add_annotations <- function(p, df2){
	if(file.exists("annotations.txt")){
		for (i in 1:nrow(df2)){
			p <- p + stat_vline(alpha = 0.2, data=df2, xintercept = df2$linepos[i], size = df2$linesize[i], colour = toString(i+1))
			if (df2$show_mean[i]) {
				p <- p + stat_vline(alpha = 0.6, data=df2, xintercept = df2$meanx[i], size = 1, colour = toString(i+1))
			}
		}
		df3 <- df2[]
		df3$type <- 'Node'
		p <- p + geom_text(alpha = 0.4, data=df3, angle = 90, aes(x=labelpos, y=max(df$value), label=annotation, hjust=1, size=6), show_guide = FALSE)
		return(p)
	}
}

mean_max_min <- function(num_columns, df){
	if (num_columns > 1000){
		tdf <- df['time']
		subdf <- df[,3:ncol(df)]
		tdf$mean <- apply(subdf,1,mean)
		tdf$max <- apply(subdf,1,max)
		tdf$min <- apply(subdf,1,min)
		return(tdf)
	} else {
		return(melt(df, id="time"))
	}
}