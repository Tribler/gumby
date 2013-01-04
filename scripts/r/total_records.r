.libPaths( c("~/R/x86_64-redhat-linux-gnu-library/2.15", .libPaths()))
is.installed <- function(mypkg) is.element(mypkg, installed.packages()[,1]) 

toInstall <- c("ggplot2", "reshape")
for (package in toInstall){
	if (is.installed(package) == FALSE){
		install.packages(package, repos = "http://cran.r-project.org", lib="~/R/x86_64-redhat-linux-gnu-library/2.15")		
	}
}
lapply(toInstall, library, character.only = TRUE)
minX <- as.integer(commandArgs(TRUE)[1])
maxX <- as.integer(commandArgs(TRUE)[2])

if(file.exists("sum_total_records.txt")){
	df <- read.table("sum_total_records.txt", header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_step(data = df, alpha = 0.5)
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Messages received by peer\n")
	p <- p + xlim(minX, maxX)
	p
	
	ggsave(file="total_records.png", width=8, height=6, dpi=100)
}