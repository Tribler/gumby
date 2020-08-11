load_annotations <- function(){
	if(file.exists("annotations.csv")){
		df2 <- read.table("annotations.csv", header = TRUE, sep=",")
		return(df2)
	}
}

add_annotations <- function(p, df, df2){
	if(file.exists("annotations.csv")){
		for (i in 1:nrow(df2)){
			p <- p + geom_vline(alpha = 0.6, xintercept=df2$time[i], size = 1, colour = toString(i+1))
			p <- p + annotate(geom="text", label=df2$name[i], x=df2$time[i] + 0.5, y=max(df$value), colour = toString(i+1), angle=90, hjust=1)
		}
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
