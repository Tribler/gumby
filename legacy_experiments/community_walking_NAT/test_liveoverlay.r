if(! "ggplot2" %in% rownames(installed.packages())) install.packages("ggplot2", repos = "http://cran.r-project.org")
if(! "reshape2" %in% rownames(installed.packages())) install.packages("reshape2", repos = "http://cran.r-project.org")
if(! "gridExtra" %in% rownames(installed.packages())) install.packages("gidExtra", repos = "http://cran.r-project.org")

library("ggplot2")
library("reshape2")
library("gridExtra")

my_graph <- function(hash, title_prefix, title_postfix, mean_threshold) {
  #hash <- "~/2782dc9253cef6cc9272ee8ed675c63743c4eb3a"
  #title_prefix <- "PREFIX"
  #title_postfix <- "POSTFIX"
  #mean_threshold <- 15
  data <- read.table(paste(hash, "_connections.txt", sep=""), header=T, quote="\"")
  data <- transform(data, TIME=as.double(TIME))


  same.as.previous <- function(x) {
    r <- rep(TRUE, nrow(x))
    r[1] <- FALSE
    for(i in 1:(nrow(x)-1))
      if(!all(x[i,] == x[i+1,]))
        r[i+1] <- FALSE
    return(r)
  }
  changes <- data[,c("TIME", "LAN_ADDRESS", "WAN_ADDRESS", "CONNECTION_TYPE")]
  changes <- changes[!same.as.previous(changes[,c("LAN_ADDRESS", "WAN_ADDRESS", "CONNECTION_TYPE")]),]
  changes$NEXT <- c(changes$TIME[-1], data[nrow(data),]$TIME)


  candidates <- data[,c("TIME", "VERIFIED_CANDIDATES", "WALK_CANDIDATES", "STUMBLE_CANDIDATES", "INTRO_CANDIDATES")]
  mcandidates <- melt(candidates, id=c("TIME"))
  breaks <- c("VERIFIED_CANDIDATES", "WALK_CANDIDATES", "STUMBLE_CANDIDATES", "INTRO_CANDIDATES")
  labels <- c("Verified", "Walk", "Stumble", "Intro")
  title <- paste(title_prefix, "candidates")
  subtitle <- title_postfix

  p <- ggplot(mcandidates, aes(TIME, value))
  p <- p + geom_line(aes(colour=variable, linetype=variable))
  p <- p + ylim(0, max(30, mcandidates$value))
  p <- p + labs(title=bquote(atop(.(title), atop(italic(.(subtitle))))))
  p <- p + labs(x="Time (seconds)", y="Candidates")
  p <- p + scale_colour_discrete(name="Candidate types", breaks=breaks, labels=labels)
  p <- p + scale_linetype_discrete(name="Candidate types", breaks=breaks, labels=labels)
  p <- p + geom_hline(yintercept=mean_threshold, colour="grey")

  # add changes to IP and NAT
  y <- max(30, mcandidates$value)
  p <- p + with(changes, geom_vline(xintercept=TIME, colour="grey"))
  p <- p + with(changes, annotate("text", x=TIME, y=y, label=paste("", CONNECTION_TYPE, "\n", LAN_ADDRESS, "\n", WAN_ADDRESS), hjust=0, vjust=0, size=4, lineheight=0.8, colour=CONNECTION_TYPE, angle=-90))
  p <- p + with(changes, annotate("segment", x=TIME, xend=NEXT, y=y, yend=y, colour=CONNECTION_TYPE))

  # add average values for 25, 50, 75, and 100% samples
  get_sample <- function(sample) {
    m = mean(sample$VERIFIED_CANDIDATES)
    c = ifelse(m < mean_threshold, "red", "darkgreen")
    p <- p + annotate("rect", alpha=0.1, fill=c, xmin=min(sample$TIME), xmax=max(sample$TIME), ymin=m, ymax=mean_threshold)
    p <- p + annotate("segment", x=min(sample$TIME), xend=max(sample$TIME), y=m, yend=m, colour=c)
  }
  p <- get_sample(candidates[1:length(candidates$TIME),])
  p <- get_sample(candidates[(0.25*length(candidates$TIME)):length(candidates$TIME),])
  p <- get_sample(candidates[(0.50*length(candidates$TIME)):length(candidates$TIME),])
  p <- get_sample(candidates[(0.75*length(candidates$TIME)):length(candidates$TIME),])
  ggsave(file=paste(hash, "_candidates.png", sep=""), width=8, height=6, dpi=100)


  walks <- data[,c("TIME", "B_ATTEMPTS", "B_SUCCESSES", "C_ATTEMPTS", "C_SUCCESSES", "INCOMING_WALKS")]
  mwalks <- melt(walks, id=c("TIME"))
  breaks <- c("B_ATTEMPTS", "B_SUCCESSES", "C_ATTEMPTS", "C_SUCCESSES", "INCOMING_WALKS")
  labels <- c("Bootstrap attampt", "Bootstrap success", "Candidate attempt", "Candiate success", "Incoming walk")
  title <- paste(title_prefix, "walker")
  subtitle <- title_postfix

  p <- ggplot(mwalks, aes(TIME, value, fill=variable))
  p <- p + geom_line(aes(colour=variable, linetype=variable))
  p <- p + ylim(0, max(30, mwalks$value))
  p <- p + labs(title=bquote(atop(.(title), atop(italic(.(subtitle))))))
  p <- p + labs(x="Time (seconds)", y="Walks")
  p <- p + scale_colour_discrete(name="Walk types", breaks=breaks, labels=labels)
  p <- p + scale_linetype_discrete(name="Walk types", breaks=breaks, labels=labels)

  # add changes to IP and NAT
  y <- max(30, mwalks$value)
  p <- p + with(changes, geom_vline(xintercept=TIME, colour="grey"))
  p <- p + with(changes, annotate("text", x=TIME, y=y, label=paste("", CONNECTION_TYPE, "\n", LAN_ADDRESS, "\n", WAN_ADDRESS), hjust=0, vjust=0, size=4, lineheight=0.8, colour=CONNECTION_TYPE, angle=-90))
  p <- p + with(changes, annotate("segment", x=TIME, xend=NEXT, y=y, yend=y, colour=CONNECTION_TYPE))
  ggsave(file=paste(hash, "_walks.png", sep=""), width=8, height=6, dpi=100)
}

tryCatch(my_graph("8164f55c2f828738fa779570e4605a81fec95c9d", "All-channel community", Sys.getenv("TITLE_POSTFIX"), 15.0), error=function(cond){return(NA)})
tryCatch(my_graph("2782dc9253cef6cc9272ee8ed675c63743c4eb3a", "Search community", Sys.getenv("TITLE_POSTFIX"), 15.0), error=function(cond){return(NA)})
tryCatch(my_graph("4fe1172862c649485c25b3d446337a35f389a2a2", "Barter community", Sys.getenv("TITLE_POSTFIX"), 15.0), error=function(cond){return(NA)})

q(save="no")
