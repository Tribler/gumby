library(ggplot2)
library(reshape)

walk_rtts <- read.table("walk_rtts.txt", header=T, quote="\"")
walk_rtts$Server <- factor(paste(walk_rtts$HOST_NAME, "\n", walk_rtts$ADDRESS, "\n", sep=''))

p <- ggplot(walk_rtts, aes(HOST_NAME, RTT))
p <- p + geom_boxplot(aes(fill=Server))
p <- p + coord_flip()
p <- p + scale_x_discrete(limits=rev(sort(walk_rtts$HOST_NAME)))
p <- p + labs(title="Bootstrap server response time", 
              x="Server address", 
              y="Round-trip time (seconds)",
              colour="Server hostname")
p
ggsave("walk_rtts.png", width=10, height=6, dpi=100)

summary <- read.table("summary.txt", header=T, quote="\"")
summary$Server <- factor(paste(summary$HOST_NAME, "\n", summary$ADDRESS, "\n", sep=''))

p <- ggplot(summary, aes(HOST_NAME, RESPONSES))
p <- p + geom_bar(aes(fill=Server))
p <- p + coord_flip()
p <- p + ylim(0, max(summary$REQUESTS))
p <- p + scale_x_discrete(limits=rev(sort(summary$HOST_NAME)))
p <- p + labs(title=paste("Bootstrap server walk request success\nout of", max(summary$REQUESTS), "requests"),
              x="Server address",
              y="Successfull walks",
              colour="Server hostname")
p


ggsave("summary.png", width=10, height=6, dpi=100)

q(save="no")
