.libPaths( c("~/R/x86_64-redhat-linux-gnu-library/2.15", .libPaths()))
is.installed <- function(mypkg) is.element(mypkg, installed.packages()[,1]) 

toInstall <- c("ggplot2", "reshape")
for (package in toInstall){
	if (is.installed(package) == FALSE){
		install.packages(package, repos = "http://cran.r-project.org", lib="~/R/x86_64-redhat-linux-gnu-library/2.15")		
	}
}
lapply(toInstall, library, character.only = TRUE)

df <- read.table("dropped_diff_reduced.txt", header = TRUE)
df <- melt(df, id="time")
df <- subset(df, df$value > 0)

p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
p <- p + geom_point(aes(size=value), alpha = 5/10) + scale_size(range = c(1, 3))
p <- p + opts(legend.position="none")
p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Messages dropped\n")
p

ggsave(file="dropped_diff.png", width=8, height=6, dpi=100)

df <- read.table("dropped_reduced.txt", header = TRUE)
df <- melt(df, id="time")

p <- ggplot(df, aes(time, value, group=variable, colour=variable)) + theme_bw()
p <- p + geom_line(alpha = 0.5)
p <- p + opts(legend.position="none")
p <- p + labs(x = "\nTime into experiment (Seconds)", y = "Messages dropped\n")
p

ggsave(file="dropped.png", width=8, height=6, dpi=100)