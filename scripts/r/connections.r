.libPaths( c("~/R/x86_64-redhat-linux-gnu-library/2.15", .libPaths()))
is.installed <- function(mypkg) is.element(mypkg, installed.packages()[,1]) 

toInstall <- c("ggplot2", "reshape")
for (package in toInstall){
	if (is.installed(package) == FALSE){
		install.packages(package, repos = "http://cran.r-project.org", lib="~/R/x86_64-redhat-linux-gnu-library/2.15")		
	}
}
lapply(toInstall, library, character.only = TRUE)

i = 1
while(file.exists(paste("total_connections_", toString(i), "_reduced.txt", sep = ''))){
	df <- read.table(paste("total_connections_", toString(i), "_reduced.txt", sep = ''), header = TRUE, check.names = FALSE)
	df <- melt(df, id="time")
	
	p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
	p <- p + geom_line(data = df, alpha = 0.5)
	p <- p + opts(legend.position="none")
	p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Connections per peer\n")
	p
	
	ggsave(file=paste("total_connections_", toString(i), ".png", sep = ''), width=8, height=6, dpi=100)
	i <- i + 1
}